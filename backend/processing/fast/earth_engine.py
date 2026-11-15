"""Precipitación, evapotranspiración y temperatura calculadas en Google Earth Engine.

Earth Engine guarda copias de los mismos productos de NASA y hace los cálculos en sus
servidores; aquí solo se descarga el resultado mensual de México.

Colecciones (catálogo de Earth Engine):
- NASA/GPM_L3/IMERG_MONTHLY_V07  (GPM_3IMERGM V07)
- MODIS/061/MOD16A2GF            (evapotranspiración, compuestos de 8 días)
- MODIS/061/MOD11A2              (temperatura de superficie, compuestos de 8 días)

Reglas científicas (idénticas al procesamiento clásico, ver docs/05-procesamiento-nasa.md):
- IMERG: mm/mes = mm/h × 24 × días del mes; valores negativos fuera. Malla nativa 0.1°
  (sin remuestreo).
- MOD16A2GF: valor × 0.1 = mm por compuesto; fuera relleno y códigos 32761–32767.
  Cada compuesto se reparte por igual entre sus días; el mes suma los días que le
  tocan y se escala a mes completo solo con ≥ 80 % de días cubiertos.
- MOD11A2: valor × 0.02 − 273.15 = °C; se acepta QC 00, o 01 con error ≤ 2 K; media
  ponderada por días; mínimo 50 % de días cubiertos. Bandera de deriva orbital ≥ 2020.
- Para MODIS el mes se calcula píxel a píxel en la resolución nativa y después se
  agrega (promedio por área) a la malla del mapa, 0.025° por defecto (≈ 2.8 km).
  Una celda del mapa necesita ≥ 50 % de su área con dato. Nunca se aumenta la resolución.
"""

from __future__ import annotations

import calendar
import logging
import os
import threading
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import numpy as np

from app.services.catalog import CatalogEntry
from app.services.dates import format_ym
from processing.common import io
from processing.common.paths import context
from processing.fast.plan import (
    DEFAULT_MAP_RES,
    Grid,
    aligned_grid,
    composite_search_window,
    composites_plan,
    months_between,
)

logger = logging.getLogger("atlas.gee")
NODATA = -9999.0
SOURCE = "earthengine"


@dataclass(frozen=True)
class EeVariable:
    variable: str
    collection: str
    native_res_deg: float
    builder: str  # nombre de la función que arma la expresión mensual
    tile: int | None  # lado máximo de cada bloque pedido (None: franjas grandes)


EE_VARIABLES = {
    "precipitation": EeVariable(
        "precipitation", "NASA/GPM_L3/IMERG_MONTHLY_V07", 0.1, "imerg", None
    ),
    "evapotranspiration": EeVariable(
        "evapotranspiration", "MODIS/061/MOD16A2GF", 1 / 240, "mod16", 256
    ),
    "temperature": EeVariable("temperature", "MODIS/061/MOD11A2", 1 / 120, "mod11", 256),
}


# ------------------------------------------------------------------------- sesión
def initialize(project: str | None = None) -> None:
    import ee

    project = project or os.environ.get("EE_PROJECT")
    if not project:
        raise RuntimeError(
            "Falta EE_PROJECT en tu .env: el ID de tu proyecto de Google Cloud registrado en "
            "Earth Engine (ver docs/09-descarga-rapida.md)."
        )
    try:
        ee.Initialize(project=project)
    except Exception as exc:  # noqa: BLE001 - el mensaje de ee es el útil
        raise RuntimeError(
            f"No se pudo iniciar Earth Engine ({exc}). Ejecuta primero "
            "`python -m processing.cli ee-login` y revisa EE_PROJECT."
        ) from exc


def authenticate() -> None:
    import ee

    ee.Authenticate()
    initialize()
    logger.info("Earth Engine listo (proyecto %s).", os.environ.get("EE_PROJECT"))


# ------------------------------------------------------------------ expresiones
def _dates_of(collection: Any) -> list[date]:
    times = collection.aggregate_array("system:time_start").getInfo() or []
    return [datetime.fromtimestamp(t / 1000, tz=UTC).date() for t in times]


def _image_on(collection: Any, day: date) -> Any:
    import ee

    nxt = day + timedelta(days=1)
    return ee.Image(collection.filterDate(day.isoformat(), nxt.isoformat()).first())


def _to_map_grid(native: Any, valid: Any, projection: Any, grid: Grid) -> Any:
    """Agrega del píxel nativo a la malla del mapa: promedio por área y fracción válida."""
    import ee

    transform = [grid.res, 0, grid.west, 0, -grid.res, grid.north]
    mean = (
        native.setDefaultProjection(projection)
        .reduceResolution(reducer=ee.Reducer.mean(), maxPixels=4096)
        .reproject(crs="EPSG:4326", crsTransform=transform)
    )
    fraction = (
        valid.toFloat()
        .setDefaultProjection(projection)
        .reduceResolution(reducer=ee.Reducer.mean(), maxPixels=4096)
        .reproject(crs="EPSG:4326", crsTransform=transform)
    )
    value = mean.updateMask(fraction.gte(0.5)).unmask(NODATA).toFloat().rename("value")
    return value.addBands(fraction.unmask(0).toFloat().rename("fraction"))


def imerg_month(year: int, month: int, grid: Grid, strict: bool = False) -> Any | None:
    import ee

    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    collection = ee.ImageCollection(EE_VARIABLES["precipitation"].collection).filterDate(
        start.isoformat(), end.isoformat()
    )
    if collection.size().getInfo() == 0:
        return None
    rate = ee.Image(collection.first()).select("precipitation")
    valid = rate.gte(0)
    hours = 24 * calendar.monthrange(year, month)[1]
    value = rate.multiply(hours).updateMask(valid).unmask(NODATA).toFloat().rename("value")
    return value.addBands(valid.unmask(0).toFloat().rename("fraction"))


def _composite_month(
    variable: str,
    year: int,
    month: int,
    grid: Grid,
    per_composite: Callable[[Any, int, int], tuple[Any, Any]],
    how: str,
    min_coverage: float,
) -> Any | None:
    import ee

    first, last = composite_search_window(year, month)
    collection = ee.ImageCollection(EE_VARIABLES[variable].collection).filterDate(
        first.isoformat(), last.isoformat()
    )
    plan = composites_plan(_dates_of(collection), year, month)
    if not plan:
        return None
    projection = ee.Image(collection.first()).select(0).projection()
    values, weights = [], []
    for use in plan:
        contribution, covered_days = per_composite(
            _image_on(collection, use.start), use.days_in_month, use.length
        )
        values.append(contribution)
        weights.append(covered_days)
    accum = ee.ImageCollection(values).sum().setDefaultProjection(projection)
    covered = ee.ImageCollection(weights).sum().setDefaultProjection(projection)
    n_days = calendar.monthrange(year, month)[1]
    if how == "sum":
        monthly = accum.multiply(n_days).divide(covered)
    else:
        monthly = accum.divide(covered)
    ok = covered.divide(n_days).gte(min_coverage)
    monthly = monthly.updateMask(ok)
    return _to_map_grid(monthly, ok.unmask(0), projection, grid)


def mod16_month(year: int, month: int, grid: Grid, strict: bool = False) -> Any | None:
    def per_composite(image: Any, days: int, length: int) -> tuple[Any, Any]:
        raw = image.select("ET")
        valid = raw.lte(32700)  # 32761–32767: relleno, agua, urbano, desierto…: no son cero
        if strict:
            valid = valid.And(image.select("ET_QC").bitwiseAnd(1).eq(0))
        valid = valid.unmask(0).toFloat()
        mm = raw.toFloat().multiply(0.1).divide(length).multiply(days)
        return mm.updateMask(valid).unmask(0), valid.multiply(days)

    return _composite_month("evapotranspiration", year, month, grid, per_composite, "sum", 0.8)


def mod11_month(year: int, month: int, grid: Grid, strict: bool = False) -> Any | None:
    def per_composite(image: Any, days: int, length: int) -> tuple[Any, Any]:
        raw = image.select("LST_Day_1km")
        quality = image.select("QC_Day")
        mandatory = quality.bitwiseAnd(3)
        lst_error = quality.rightShift(6).bitwiseAnd(3)
        good = mandatory.eq(0).Or(mandatory.eq(1).And(lst_error.lte(1)))
        valid = raw.gte(7500).And(good).unmask(0).toFloat()
        celsius = raw.toFloat().multiply(0.02).subtract(273.15)
        return celsius.multiply(days).updateMask(valid).unmask(0), valid.multiply(days)

    return _composite_month("temperature", year, month, grid, per_composite, "mean", 0.5)


BUILDERS = {"imerg": imerg_month, "mod16": mod16_month, "mod11": mod11_month}


# -------------------------------------------------------------------- descarga
_RETRYABLE = (
    "too many",
    "429",
    "rate",
    "quota",
    "deadline",
    "timed out",
    "internal",
    "503",
    "500",
    "unavailable",
)


_MEMORY = ("memory limit", "memory", "too large", "computation timed out")
MIN_TILE = 32


def _request(expression: Any, grid: Grid, r0: int, rows: int, c0: int, cols: int) -> Any:
    import ee

    request = {
        "expression": expression,
        "fileFormat": "NUMPY_NDARRAY",
        "grid": {
            "dimensions": {"width": cols, "height": rows},
            "affineTransform": grid.affine(r0, c0),
            "crsCode": "EPSG:4326",
        },
    }
    for attempt in range(1, 7):
        try:
            return ee.data.computePixels(request)
        except Exception as exc:  # noqa: BLE001 - ee y requests lanzan varios tipos
            message = str(exc).lower()
            if any(word in message for word in _MEMORY):
                raise MemoryError(message) from exc
            if attempt < 6 and any(word in message for word in _RETRYABLE):
                time.sleep(min(60, 3 * 2**attempt))
                continue
            raise
    raise RuntimeError("Earth Engine no respondió después de varios intentos.")


def _fetch_block(
    expression: Any,
    grid: Grid,
    block: tuple[int, int, int, int],
    value: np.ndarray,
    fraction: np.ndarray,
) -> None:
    """Pide un bloque; si Earth Engine se queda sin memoria, lo parte en 4 y reintenta."""
    r0, rows, c0, cols = block
    try:
        array = _request(expression, grid, r0, rows, c0, cols)
    except MemoryError:
        if rows <= MIN_TILE and cols <= MIN_TILE:
            raise
        half_r, half_c = max(1, rows // 2), max(1, cols // 2)
        for sub in (
            (r0, half_r, c0, half_c),
            (r0, half_r, c0 + half_c, cols - half_c),
            (r0 + half_r, rows - half_r, c0, half_c),
            (r0 + half_r, rows - half_r, c0 + half_c, cols - half_c),
        ):
            if sub[1] > 0 and sub[3] > 0:
                _fetch_block(expression, grid, sub, value, fraction)
        return
    tile_value = np.asarray(array["value"], dtype="float32")
    value[r0 : r0 + rows, c0 : c0 + cols] = np.where(tile_value <= NODATA + 1, np.nan, tile_value)
    fraction[r0 : r0 + rows, c0 : c0 + cols] = np.asarray(array["fraction"], dtype="float32")


def compute_pixels(
    expression: Any, grid: Grid, tile: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Descarga (valor, fracción) de la malla completa, por bloques."""
    value = np.full((grid.height, grid.width), np.nan, dtype="float32")
    fraction = np.zeros((grid.height, grid.width), dtype="float32")
    for block in grid.tiles(tile):
        _fetch_block(expression, grid, block, value, fraction)
    return value, fraction


# ------------------------------------------------------------------- escritura
_catalog_lock = threading.Lock()


def _write_month(
    variable: str, year: int, month: int, grid: Grid, value: np.ndarray, fraction: np.ndarray
) -> CatalogEntry:
    paths, products, _ = context()
    p = products.get(variable)
    date_text = format_ym(year, month)
    lats, lons = io.grid_coords(grid.west, grid.north, grid.res, grid.res, grid.width, grid.height)
    nc_path = io.write_monthly_netcdf(
        paths.processed_monthly(variable) / f"{variable}_{date_text}.nc",
        variable,
        value,
        lats,
        lons,
        year,
        month,
        p["unit"],
        {
            "source_product": f"{p['product']['short_name']} v{p['product']['version']}",
            "processing_platform": f"Google Earth Engine ({EE_VARIABLES[variable].collection})",
            "method": p["processing"]["monthly_method"],
            "quality_filter": p["processing"]["quality_filter"],
            "map_resolution_deg": grid.res,
        },
        {"valid_fraction": (fraction, "1")},
    )
    cog_path = io.write_cog(
        paths.cog(variable) / f"{variable}_{date_text}.tif",
        value,
        grid.west,
        grid.north,
        grid.res,
        grid.res,
    )
    n_valid, coverage = io.valid_summary(value)
    flags = ["deriva_orbital_terra"] if variable == "temperature" and year >= 2020 else []
    native = EE_VARIABLES[variable].native_res_deg
    notes = [f"Calculado en Google Earth Engine a partir de {EE_VARIABLES[variable].collection}."]
    if grid.res > native * 1.01:
        notes.append(
            f"Mapa agregado de la resolución nativa (~{native:.4f}°) a {grid.res}° por promedio de área."
        )
    entry = CatalogEntry(
        variable=variable,
        level="native",
        date=date_text,
        product=p["product"]["short_name"],
        version=p["product"]["version"],
        path=paths.relative(cog_path),
        format="cog",
        units=p["unit"],
        resolution_deg=grid.res,
        n_valid=n_valid,
        coverage=coverage,
        quality={
            "netcdf": paths.relative(nc_path),
            "source": SOURCE,
            "flags": flags,
            "notes": notes,
        },
    )
    with _catalog_lock:
        catalog = context()[2]  # releer: otros hilos pudieron escribir
        catalog.add(entry)
        catalog.save()
    return entry


def grid_for(variable: str, map_res: float) -> Grid:
    native = EE_VARIABLES[variable].native_res_deg
    if variable == "precipitation":
        return aligned_grid(native)
    if map_res < native * 0.999:
        raise ValueError(
            f"La resolución de mapa {map_res}° es más fina que la nativa de {variable} "
            f"({native:.4f}°): eso sería inventar detalle. Usa un valor ≥ {native:.4f}."
        )
    return aligned_grid(map_res)


def run(
    variables: list[str],
    start: str,
    end: str,
    map_res: float = DEFAULT_MAP_RES,
    workers: int = 6,
    force: bool = False,
    strict: bool = False,
) -> int:
    initialize()
    paths, products, catalog = context()
    tasks = []
    for variable in variables:
        grid = grid_for(variable, map_res)
        for year, month in months_between(start, end):
            if not products.is_available(variable, year, month):
                continue
            existing = catalog.find(variable, "native", format_ym(year, month))
            if (
                not force
                and existing is not None
                and existing.quality.get("source") == SOURCE
                and abs((existing.resolution_deg or 0) - grid.res) < 1e-9
                and (paths.root / existing.path).exists()
            ):
                continue
            tasks.append((variable, year, month, grid))
    if not tasks:
        logger.info("Earth Engine: no hay meses pendientes en ese rango.")
        return 0
    logger.info("Earth Engine: %d meses por calcular con %d hilos.", len(tasks), workers)

    def work(variable: str, year: int, month: int, grid: Grid) -> str:
        began = time.monotonic()
        builder = BUILDERS[EE_VARIABLES[variable].builder]
        expression = builder(year, month, grid, strict)
        if expression is None:
            return f"{variable} {year}-{month:02d}: Earth Engine no tiene imágenes; se omite"
        value, fraction = compute_pixels(expression, grid, EE_VARIABLES[variable].tile)
        _write_month(variable, year, month, grid, value, fraction)
        return f"{variable} {year}-{month:02d} listo ({time.monotonic() - began:.0f} s)"

    done, failed = 0, []
    pool = ThreadPoolExecutor(max_workers=workers)
    futures = {pool.submit(work, *task): task for task in tasks}
    pending = set(futures)
    number = 0
    try:
        while pending:
            # Espera en pasos de 1 s para que Ctrl + C funcione también en Windows.
            finished, pending = wait(pending, timeout=1.0, return_when=FIRST_COMPLETED)
            for future in finished:
                number += 1
                variable, year, month, _ = futures[future]
                try:
                    logger.info("[%d/%d] %s", number, len(tasks), future.result())
                    done += 1
                except Exception as exc:  # noqa: BLE001 - se reporta y se sigue con los demás
                    failed.append(f"{variable} {year}-{month:02d}")
                    logger.error(
                        "[%d/%d] %s %d-%02d falló: %s",
                        number,
                        len(tasks),
                        variable,
                        year,
                        month,
                        exc,
                    )
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    if failed:
        logger.warning(
            "Fallaron %d meses: %s. Vuelve a ejecutar el mismo comando: solo repetirá esos.",
            len(failed),
            ", ".join(failed[:20]) + ("…" if len(failed) > 20 else ""),
        )
    return done
