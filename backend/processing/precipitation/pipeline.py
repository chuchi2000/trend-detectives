"""Precipitación: GPM IMERG Final V07 mensual (GPM_3IMERGM).

Descarga  -> data/raw/precipitation/            archivos HDF5 originales (globales)
Proceso   -> data/processed/monthly/precipitation/precipitation_AAAA-MM.nc
             data/optimized/cog/precipitation/precipitation_AAAA-MM.tif
Catálogo  -> data/catalog/catalog.json (nivel "native")

Pasos científicos:
1. Leer Grid/precipitation (mm/h, tasa media del mes) y sus capas de calidad.
2. Recortar a la caja de México conservando la malla nativa de 0.1°.
3. Descartar el relleno (-9999.9) y los negativos; NO se convierten en cero.
4. Convertir a mm/mes = mm/h × 24 × días del mes.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np

from app.services.catalog import CatalogEntry
from app.services.dates import format_ym, iter_months
from processing.common import io, qc
from processing.common.earthdata import login
from processing.common.paths import MEXICO_BBOX, context
from processing.common.temporal import rate_to_monthly_total

VARIABLE = "precipitation"
logger = logging.getLogger("atlas.precipitation")


def download(start: str, end: str) -> list[Path]:
    """Busca y descarga los archivos mensuales de IMERG entre dos meses (AAAA-MM)."""
    import earthaccess

    paths, products, _ = context()
    product = products.get(VARIABLE)["product"]
    login()
    results = earthaccess.search_data(
        short_name=product["short_name"],
        version=product["version"],
        temporal=(f"{start}-01", f"{end}-28"),
        bounding_box=MEXICO_BBOX,
    )
    logger.info("IMERG: %d archivos encontrados entre %s y %s", len(results), start, end)
    target = paths.raw(VARIABLE)
    target.mkdir(parents=True, exist_ok=True)
    files = earthaccess.download(results, local_path=str(target))
    return [Path(f) for f in files]


def _month_from_name(path: Path) -> tuple[int, int] | None:
    # Nombre típico: 3B-MO.MS.MRG.3IMERG.20150701-S000000-E235959.07.V07B.HDF5
    match = re.search(r"\.(\d{4})(\d{2})01-S", path.name)
    return (int(match.group(1)), int(match.group(2))) if match else None


def _mexico_layer(ds, name: str):  # noqa: ANN001, ANN202 - tipos de xarray importados al vuelo
    """Una capa de IMERG recortada a México y ordenada como imagen (lat, lon), norte arriba.

    Se trabaja capa por capa: el grupo Grid también trae variables de límites de celda
    (lat_bnds, lon_bnds, time_bnds) con dimensiones extra (latv, lonv, nv), así que no se
    puede reordenar el Dataset completo. IMERG guarda (time, lon, lat) con latitudes
    ascendentes.
    """
    west, south, east, north = MEXICO_BBOX
    da = ds[name]
    if "time" in da.dims:
        da = da.isel(time=0)
    da = da.sel(lon=slice(west, east), lat=slice(south, north))
    extra = [d for d in da.dims if d not in ("lat", "lon")]
    if extra:
        raise RuntimeError(f"La capa {name} de IMERG tiene dimensiones inesperadas: {da.dims}")
    return da.transpose("lat", "lon").sortby("lat", ascending=False)


def process_file(path: Path) -> CatalogEntry:
    import xarray as xr

    paths, products, catalog = context()
    p = products.get(VARIABLE)
    ds = xr.open_dataset(path, group="Grid", engine="h5netcdf")
    year_month = _month_from_name(path)
    if year_month is None:
        first = np.datetime64(ds["time"].values[0], "M").astype(str)
        year_month = (int(first[:4]), int(first[5:7]))
    year, month = year_month
    products.require_available(VARIABLE, year, month)

    precip = _mexico_layer(ds, "precipitation")
    rate = precip.values.astype("float32")
    valid = qc.imerg_valid(rate)
    rate = np.where(valid, rate, np.nan)
    monthly = rate_to_monthly_total(rate, year, month)

    lats = precip["lat"].values
    lons = precip["lon"].values
    res = float(abs(lons[1] - lons[0]))
    date = format_ym(year, month)
    quality_layers = {}
    for name in ("randomError", "precipitationQualityIndex"):
        if name in ds.data_vars:
            layer_da = _mexico_layer(ds, name)
            layer = layer_da.values.astype("float32")
            quality_layers[name] = (
                np.where(layer > qc.IMERG_FILL + 1, layer, np.nan),
                layer_da.attrs.get("units", ""),
            )

    nc_path = io.write_monthly_netcdf(
        paths.processed_monthly(VARIABLE) / f"{VARIABLE}_{date}.nc",
        VARIABLE,
        monthly,
        lats,
        lons,
        year,
        month,
        p["unit"],
        {
            "source_product": f"{p['product']['short_name']} v{p['product']['version']}",
            "source_file": path.name,
            "method": p["processing"]["conversion"],
        },
        quality_layers,
    )
    cog_path = io.write_cog(
        paths.cog(VARIABLE) / f"{VARIABLE}_{date}.tif",
        monthly,
        float(lons[0] - res / 2),
        float(lats[0] + res / 2),
        res,
        res,
    )
    n_valid, coverage = io.valid_summary(monthly)
    entry = CatalogEntry(
        variable=VARIABLE,
        level="native",
        date=date,
        product=p["product"]["short_name"],
        version=p["product"]["version"],
        path=paths.relative(cog_path),
        format="cog",
        units=p["unit"],
        resolution_deg=res,
        n_valid=n_valid,
        coverage=coverage,
        quality={
            "netcdf": paths.relative(nc_path),
            "flags": [],
            "notes": ["Estimación satelital calibrada con pluviómetros (IMERG Final)."],
        },
    )
    catalog.add(entry)
    catalog.save()
    logger.info("Precipitación %s procesada (%d píxeles válidos).", date, n_valid)
    return entry


def process(start: str, end: str) -> list[CatalogEntry]:
    paths, _, _ = context()
    wanted = {m for m in iter_months(start, end)}
    files = sorted(paths.raw(VARIABLE).glob("*.HDF5")) + sorted(paths.raw(VARIABLE).glob("*.h5"))
    entries = []
    for file in files:
        ym = _month_from_name(file)
        if ym is None or ym in wanted:
            entries.append(process_file(file))
    if not entries:
        logger.warning(
            "No hay archivos de IMERG para %s–%s en %s. ¿Ejecutaste la descarga?",
            start,
            end,
            paths.raw(VARIABLE),
        )
    return entries
