"""Flujo compartido para productos MODIS de 8 días (MOD16A2GF y MOD11A2).

Descarga: AppEEARS, una solicitud de área por año, en GeoTIFF y coordenadas
geográficas (EPSG:4326). AppEEARS entrega una capa de valor y otra de calidad
por compuesto, con nombres que incluyen el día juliano: "..._doy2015193_...".

Proceso: para cada mes se leen los compuestos que lo tocan, se aplican el
factor de escala y los filtros de calidad, y se calcula el valor mensual con
processing.common.temporal. Se trabaja por bloques de filas para no cargar
todo México a 500 m en memoria de una sola vez.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

import numpy as np

from app.services.catalog import CatalogEntry
from app.services.dates import format_ym
from processing.common import io
from processing.common.appeears import AppEEARSClient, area_task
from processing.common.paths import MEXICO_BBOX, context
from processing.common.temporal import composites_for_month, doy_to_date, monthly_from_composites

logger = logging.getLogger("atlas.modis")
DOY = re.compile(r"doy(\d{4})(\d{3})")


@dataclass(frozen=True)
class ModisSpec:
    variable: str
    appeears_product: str  # p. ej. "MOD11A2.061"
    value_layer: str
    qc_layer: str
    how: Literal["sum", "mean"]
    min_coverage: float
    # (valores_crudos, qc) -> (valores_físicos con NaN, máscara de "otra calidad" o None)
    convert: Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray | None]]


def year_ranges(start: str, end: str) -> list[tuple[int, date, date]]:
    """Fechas a pedir por año: desde 7 días antes del primer mes (un compuesto puede
    empezar en el mes anterior) hasta el último día del último mes."""
    from datetime import timedelta

    from app.services.dates import days_in_month, parse_ym

    y0, m0 = parse_ym(start)
    y1, m1 = parse_ym(end)
    first_day = date(y0, m0, 1) - timedelta(days=7)
    last_day = date(y1, m1, days_in_month(y1, m1))
    ranges = []
    for year in range(y0, y1 + 1):
        ranges.append((year, max(first_day, date(year, 1, 1)), min(last_day, date(year, 12, 31))))
    return ranges


MARKER = "_descarga_completa.json"


def marker_covers(folder: Path, start: date, end: date) -> bool:
    """True si una descarga anterior terminada cubre todo el intervalo pedido."""
    import json

    marker = folder / MARKER
    if not marker.exists():
        return False
    try:
        info = json.loads(marker.read_text(encoding="utf-8"))
        return date.fromisoformat(info["start"]) <= start and date.fromisoformat(info["end"]) >= end
    except (ValueError, KeyError, TypeError):
        return False


def download_year(
    spec: ModisSpec, year: int, first: date | None = None, last: date | None = None
) -> list[Path]:
    import json

    paths, _, _ = context()
    start = first or date(year, 1, 1)
    end = last or date(year, 12, 31)
    folder = paths.raw(spec.variable) / str(year)
    if marker_covers(folder, start, end):
        logger.info(
            "%s %d: ya descargado de %s a %s; se omite. Borra %s para repetir.",
            spec.variable,
            year,
            start,
            end,
            MARKER,
        )
        return sorted(folder.rglob("*.tif"))
    client = AppEEARSClient()
    client.login()
    try:
        task = area_task(
            name=f"atlas_{spec.variable}_{year}",
            product=spec.appeears_product,
            layers=[spec.value_layer, spec.qc_layer],
            start=start,
            end=end,
            bbox=MEXICO_BBOX,
        )
        task_id = client.submit(task)
        client.wait(task_id)
        files = client.download_bundle(task_id, folder)
        (folder / MARKER).write_text(
            json.dumps({"start": start.isoformat(), "end": end.isoformat(), "task_id": task_id}),
            encoding="utf-8",
        )
        return files
    finally:
        client.logout()


def _index_files(folder: Path, layer: str) -> dict[date, Path]:
    found: dict[date, Path] = {}
    for path in folder.rglob("*.tif"):
        if layer not in path.name:
            continue
        match = DOY.search(path.name)
        if match:
            found[doy_to_date(int(match.group(1)), int(match.group(2)))] = path
    return dict(sorted(found.items()))


def process_month(spec: ModisSpec, year: int, month: int, block_rows: int = 1024) -> CatalogEntry:
    import rasterio
    from rasterio.windows import Window

    paths, products, catalog = context()
    p = products.get(spec.variable)
    products.require_available(spec.variable, year, month)
    folder = paths.raw(spec.variable) / str(year)
    values_by_date = _index_files(folder, spec.value_layer)
    qc_by_date = _index_files(folder, spec.qc_layer)
    starts = [d for d in values_by_date if d in qc_by_date]
    selected = composites_for_month(starts, year, month)
    if not selected:
        raise FileNotFoundError(
            f"No hay compuestos de {spec.variable} para {year}-{month:02d} en {folder}."
        )
    used = [starts[i] for i, _, _ in selected]

    with rasterio.open(values_by_date[used[0]]) as ref:
        height, width, transform = ref.height, ref.width, ref.transform
    result = np.full((height, width), np.nan, dtype="float32")
    coverage = np.zeros((height, width), dtype="float32")
    other_quality = np.zeros((height, width), dtype="float32")

    sources = [(rasterio.open(values_by_date[d]), rasterio.open(qc_by_date[d])) for d in used]
    try:
        for r0 in range(0, height, block_rows):
            window = Window(0, r0, width, min(block_rows, height - r0))
            stack, flags = [], []
            for value_src, qc_src in sources:
                raw = value_src.read(1, window=window)
                qc_block = qc_src.read(1, window=window)
                physical, other = spec.convert(raw, qc_block)
                stack.append(physical)
                flags.append(np.zeros_like(physical) if other is None else other.astype("float32"))
            monthly, cov = monthly_from_composites(
                np.stack(stack), used, year, month, spec.how, spec.min_coverage
            )
            rows = slice(r0, r0 + window.height)
            result[rows] = monthly
            coverage[rows] = cov
            other_quality[rows] = np.mean(np.stack(flags), axis=0)
    finally:
        for value_src, qc_src in sources:
            value_src.close()
            qc_src.close()

    res_x, res_y = abs(transform.a), abs(transform.e)
    west, north = transform.c, transform.f
    lats, lons = io.grid_coords(west, north, res_x, res_y, width, height)
    date_text = format_ym(year, month)
    nc_path = io.write_monthly_netcdf(
        paths.processed_monthly(spec.variable) / f"{spec.variable}_{date_text}.nc",
        spec.variable,
        result,
        lats,
        lons,
        year,
        month,
        p["unit"],
        {
            "source_product": f"{p['product']['short_name']} v{p['product']['version']}",
            "composites_used": ", ".join(d.isoformat() for d in used),
            "method": p["processing"]["monthly_method"],
            "quality_filter": p["processing"]["quality_filter"],
        },
        {"coverage": (coverage, "1"), "other_quality_fraction": (other_quality, "1")},
    )
    cog_path = io.write_cog(
        paths.cog(spec.variable) / f"{spec.variable}_{date_text}.tif",
        result,
        west,
        north,
        res_x,
        res_y,
    )
    n_valid, cov_fraction = io.valid_summary(result)
    entry = CatalogEntry(
        variable=spec.variable,
        level="native",
        date=date_text,
        product=p["product"]["short_name"],
        version=p["product"]["version"],
        path=paths.relative(cog_path),
        format="cog",
        units=p["unit"],
        resolution_deg=res_x,
        n_valid=n_valid,
        coverage=cov_fraction,
        quality={
            "netcdf": paths.relative(nc_path),
            "composites_used": [d.isoformat() for d in used],
            "min_coverage_days": spec.min_coverage,
            "flags": ["deriva_orbital_terra"]
            if (spec.variable == "temperature" and year >= 2020)
            else [],
            "notes": [
                f"Mes calculado a partir de {len(used)} compuestos de 8 días ponderados por días en el mes."
            ],
        },
    )
    catalog.add(entry)
    catalog.save()
    logger.info(
        "%s %s procesado con %d compuestos (%d píxeles válidos).",
        spec.variable,
        date_text,
        len(used),
        n_valid,
    )
    return entry
