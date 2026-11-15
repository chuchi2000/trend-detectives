"""NO₂: OMI/Aura OMNO2d (diario, 0.25°), columna troposférica con filtro de nubes.

Descarga  -> archivos diarios globales (temporales) -> se recortan a México y se
             guardan juntos por mes en data/raw/no2/OMNO2d_<versión>_mexico_AAAA-MM.nc
             (valores originales, sin promediar). Los globales se borran salvo
             que se pida conservarlos, porque pesan ~12 MB por día.
Proceso   -> promedio mensual por celda + número de días válidos + cobertura.

Pasos científicos:
1. Variable ColumnAmountNO2TropCloudScreened: el productor ya filtró fracción
   de nubes < 30 %, ángulo cenital solar ≤ 85°, banderas de calidad y
   anomalía de filas del detector.
2. Se descarta el valor de relleno; NO se convierte en cero.
3. Promedio de los días válidos; si una celda tiene menos de `min_days`
   días válidos el mes queda sin dato (por defecto 3).
"""

from __future__ import annotations

import logging
import re
import shutil
from datetime import date
from pathlib import Path

import numpy as np

from app.services.catalog import CatalogEntry
from app.services.dates import days_in_month, format_ym, iter_months
from processing.common import io, qc
from processing.common.earthdata import login
from processing.common.paths import MEXICO_BBOX, context

VARIABLE = "no2"
FIELD_SUFFIX = "ColumnAmountNO2TropCloudScreened"
logger = logging.getLogger("atlas.no2")


def _find_dataset(h5: object, suffix: str) -> object:
    found: list[object] = []

    def visitor(name: str, obj: object) -> None:
        if name.endswith(suffix) and hasattr(obj, "shape"):
            found.append(obj)

    h5.visititems(visitor)  # type: ignore[attr-defined]
    if not found:
        raise KeyError(f"No se encontró {suffix} en el archivo.")
    return found[0]


def read_daily_subset(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Lee la columna troposférica de un archivo diario y la recorta a México.

    La malla global de OMNO2d es de 0.25°: 720 filas desde −90° (sur) y 1440
    columnas desde −180°. Se devuelve con el norte arriba.
    """
    import h5py

    with h5py.File(path, "r") as h5:
        data = np.asarray(_find_dataset(h5, FIELD_SUFFIX)[()], dtype="float32")
    ny, nx = data.shape
    res = 180.0 / ny
    lats = -90 + res * (np.arange(ny) + 0.5)
    lons = -180 + res * (np.arange(nx) + 0.5)
    west, south, east, north = MEXICO_BBOX
    rows = np.where((lats > south) & (lats < north))[0]
    cols = np.where((lons > west) & (lons < east))[0]
    sub = data[rows.min() : rows.max() + 1, cols.min() : cols.max() + 1]
    sub = np.where(qc.omi_valid(sub), sub, np.nan)[::-1]
    return sub, lats[rows][::-1], lons[cols]


def _day_from_name(path: Path) -> date | None:
    # Nombre típico: OMI-Aura_L3-OMNO2d_2015m0701_v004-....he5
    match = re.search(r"_(\d{4})m(\d{2})(\d{2})_", path.name)
    return date(int(match.group(1)), int(match.group(2)), int(match.group(3))) if match else None


def download_month(year: int, month: int, keep_global: bool = False) -> Path:
    import earthaccess
    import xarray as xr

    paths, products, _ = context()
    products.require_available(VARIABLE, year, month)
    product = products.get(VARIABLE)["product"]
    out = paths.raw(VARIABLE) / f"OMNO2d_{product['version']}_mexico_{year:04d}-{month:02d}.nc"
    if out.exists():
        logger.info(
            "OMNO2d %04d-%02d ya descargado (%s); se omite. Bórralo para repetir.",
            year,
            month,
            out.name,
        )
        return out
    login()
    last = days_in_month(year, month)
    results = earthaccess.search_data(
        short_name=product["short_name"],
        version=product["version"],
        temporal=(f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last:02d}"),
    )
    logger.info("OMNO2d %04d-%02d: %d archivos diarios", year, month, len(results))
    tmp = paths.raw(VARIABLE) / "_globales" / f"{year:04d}-{month:02d}"
    tmp.mkdir(parents=True, exist_ok=True)
    files = sorted(Path(f) for f in earthaccess.download(results, local_path=str(tmp)))

    days, layers = [], []
    lats = lons = None
    for file in files:
        day = _day_from_name(file)
        if day is None:
            continue
        sub, lats, lons = read_daily_subset(file)
        days.append(np.datetime64(day))
        layers.append(sub)
    if not layers:
        raise RuntimeError(f"No se pudo leer ningún archivo diario de {year}-{month:02d}.")

    ds = xr.Dataset(
        {FIELD_SUFFIX: (("time", "lat", "lon"), np.stack(layers), {"units": "molec/cm2"})},
        coords={"time": np.array(days), "lat": lats, "lon": lons},
        attrs={
            "source_product": f"OMNO2d v{product['version']}",
            "note": "Recorte a México de los archivos diarios; valores originales.",
        },
    )
    ds.to_netcdf(out, encoding={FIELD_SUFFIX: {"zlib": True, "complevel": 4}})
    if not keep_global:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def download(start: str, end: str, keep_global: bool = False) -> list[Path]:
    return [download_month(y, m, keep_global) for y, m in iter_months(start, end)]


def monthly_mean(daily: np.ndarray, min_days: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Promedio de días válidos y conteo de días válidos por celda."""
    valid = np.isfinite(daily)
    n_valid = valid.sum(axis=0)
    total = np.where(valid, daily, 0.0).sum(axis=0, dtype="float64")
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = total / n_valid
    mean = np.where(n_valid >= min_days, mean, np.nan)
    return mean.astype("float32"), n_valid.astype("int16")


def process_month(year: int, month: int, min_days: int = 3) -> CatalogEntry:
    import xarray as xr

    paths, products, catalog = context()
    p = products.get(VARIABLE)
    version = p["product"]["version"]
    raw = paths.raw(VARIABLE) / f"OMNO2d_{version}_mexico_{year:04d}-{month:02d}.nc"
    if not raw.is_file():
        raise FileNotFoundError(f"Falta {raw.name}; ejecuta primero la descarga de ese mes.")
    ds = xr.open_dataset(raw)
    daily = ds[FIELD_SUFFIX].values.astype("float32")
    lats, lons = ds["lat"].values, ds["lon"].values
    mean, n_valid_days = monthly_mean(daily, min_days)
    coverage_days = n_valid_days / days_in_month(year, month)
    date_text = format_ym(year, month)
    res = float(abs(lons[1] - lons[0]))

    nc_path = io.write_monthly_netcdf(
        paths.processed_monthly(VARIABLE) / f"{VARIABLE}_{date_text}.nc",
        VARIABLE,
        mean,
        lats,
        lons,
        year,
        month,
        p["unit"],
        {
            "source_product": f"OMNO2d v{version}",
            "method": p["processing"]["monthly_method"],
            "min_valid_days": min_days,
        },
        {
            "n_valid_days": (n_valid_days.astype("float32"), "días"),
            "coverage": (coverage_days.astype("float32"), "1"),
        },
    )
    cog_path = io.write_cog(
        paths.cog(VARIABLE) / f"{VARIABLE}_{date_text}.tif",
        mean,
        float(lons[0] - res / 2),
        float(lats[0] + res / 2),
        res,
        res,
    )
    n_valid, coverage = io.valid_summary(mean)
    entry = CatalogEntry(
        variable=VARIABLE,
        level="native",
        date=date_text,
        product=p["product"]["short_name"],
        version=version,
        path=paths.relative(cog_path),
        format="cog",
        units=p["unit"],
        resolution_deg=res,
        n_valid=n_valid,
        coverage=coverage,
        quality={
            "netcdf": paths.relative(nc_path),
            "min_valid_days": min_days,
            "mean_valid_days": float(n_valid_days[n_valid_days > 0].mean())
            if (n_valid_days > 0).any()
            else 0.0,
            "flags": [],
            "notes": [f"Promedio de días válidos; mínimo {min_days} días por celda."],
        },
    )
    catalog.add(entry)
    catalog.save()
    logger.info("NO₂ %s procesado (%d celdas válidas).", date_text, n_valid)
    return entry


def process(start: str, end: str, min_days: int = 3) -> list[CatalogEntry]:
    return [process_month(y, m, min_days) for y, m in iter_months(start, end)]
