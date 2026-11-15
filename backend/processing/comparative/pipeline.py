"""Homologación: todos los meses de todas las variables en la malla común de 0.25°.

Lee los NetCDF mensuales de cada variable, los agrega de forma conservativa a
la malla común (processing/common/regrid.py) y escribe un cubo por variable en
data/processed/comparative/<variable>_0p25.nc, con su entrada de catálogo de
nivel "comparative". La API usa estos cubos para series, estadísticas,
comparaciones y correlaciones.

Nunca se sobremuestrea: NO₂ ya está en 0.25° y solo se recorta.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np

from app.services.catalog import CatalogEntry
from app.services.grid import CommonGrid
from processing.common.paths import context
from processing.common.regrid import conservative_regrid, edges_from_centers

logger = logging.getLogger("atlas.comparative")
MONTH_IN_NAME = re.compile(r"_(\d{4})-(\d{2})\.nc$")


def common_grid() -> CommonGrid:
    _, products, _ = context()
    cfg = products.common_grid
    return CommonGrid.from_bounds(cfg["bounds"], cfg["resolution_deg"])


def build_variable(variable: str, min_valid_fraction: float = 0.5) -> CatalogEntry | None:
    import xarray as xr

    paths, products, catalog = context()
    grid = common_grid()
    files = sorted(paths.processed_monthly(variable).glob(f"{variable}_*.nc"))
    if not files:
        logger.warning("No hay NetCDF mensuales de %s; procesa esa variable primero.", variable)
        return None

    dst_lat_edges = np.concatenate([grid.lats + grid.res / 2, [grid.lats[-1] - grid.res / 2]])
    dst_lon_edges = np.concatenate([grid.lons - grid.res / 2, [grid.lons[-1] + grid.res / 2]])

    dates: list[np.datetime64] = []
    fields: list[np.ndarray] = []
    fractions: list[np.ndarray] = []
    for file in files:
        match = MONTH_IN_NAME.search(file.name)
        if not match:
            continue
        ds = xr.open_dataset(file)
        data = ds[variable].isel(time=0).values.astype("float32")
        src_lat_edges = edges_from_centers(ds["lat"].values)
        src_lon_edges = edges_from_centers(ds["lon"].values)
        native_res = float(abs(ds["lon"].values[1] - ds["lon"].values[0]))
        if abs(native_res - grid.res) < 1e-9:
            # Ya está en 0.25°: se alinea por índice en lugar de regrillar.
            regridded, fraction = _align(data, ds["lat"].values, ds["lon"].values, grid)
        else:
            regridded, fraction = conservative_regrid(
                data, src_lat_edges, src_lon_edges, dst_lat_edges, dst_lon_edges, min_valid_fraction
            )
        dates.append(np.datetime64(f"{match.group(1)}-{match.group(2)}-01"))
        fields.append(regridded)
        fractions.append(fraction)
        ds.close()

    if not fields:
        return None

    p = products.get(variable)
    out = paths.comparative_nc / f"{variable}_0p25.nc"
    out.parent.mkdir(parents=True, exist_ok=True)
    cube = xr.Dataset(
        {
            variable: (("time", "lat", "lon"), np.stack(fields), {"units": p["unit"]}),
            "valid_fraction": (("time", "lat", "lon"), np.stack(fractions), {"units": "1"}),
        },
        coords={"time": np.array(dates), "lat": grid.lats, "lon": grid.lons},
        attrs={
            "title": f"Atlas Ambiental de México — {variable} en malla común de 0.25°",
            "source_product": f"{p['product']['short_name']} v{p['product']['version']}",
            "method": p["processing"]["comparative"],
            "min_valid_fraction": min_valid_fraction,
        },
    )
    cube.to_netcdf(
        out,
        encoding={
            variable: {"zlib": True, "complevel": 4},
            "valid_fraction": {"zlib": True, "complevel": 4},
        },
    )
    entry = CatalogEntry(
        variable=variable,
        level="comparative",
        date=None,
        product=p["product"]["short_name"],
        version=p["product"]["version"],
        path=paths.relative(out),
        format="netcdf",
        units=p["unit"],
        resolution_deg=grid.res,
        start=str(min(dates))[:7],
        end=str(max(dates))[:7],
        n_valid=len(dates),
        quality={
            "min_valid_fraction": min_valid_fraction,
            "flags": [],
            "notes": ["Agregación conservativa ponderada por área a 0.25°."],
        },
    )
    catalog.add(entry)
    catalog.save()
    logger.info("Cubo comparativo de %s: %d meses -> %s", variable, len(dates), out.name)
    return entry


def _align(
    data: np.ndarray, lats: np.ndarray, lons: np.ndarray, grid: CommonGrid
) -> tuple[np.ndarray, np.ndarray]:
    """Coloca un campo que ya está en 0.25° dentro de la malla común."""
    out = np.full(grid.shape, np.nan, dtype="float32")
    for i, lat in enumerate(lats):
        row = int(round((grid.north - float(lat) - grid.res / 2) / grid.res))
        if not 0 <= row < grid.shape[0]:
            continue
        for j, lon in enumerate(lons):
            col = int(round((float(lon) - grid.west - grid.res / 2) / grid.res))
            if 0 <= col < grid.shape[1]:
                out[row, col] = data[i, j]
    return out, np.isfinite(out).astype("float32")


def build_all(variables: list[str] | None = None) -> list[CatalogEntry]:
    _, products, _ = context()
    entries = []
    for variable in variables or products.variable_ids:
        entry = build_variable(variable)
        if entry:
            entries.append(entry)
    return entries


def export_zarr(variable: str) -> Path | None:
    """Copia opcional en Zarr, útil cuando el cubo crece (lectura por trozos)."""
    import xarray as xr

    paths, _, _ = context()
    source = paths.comparative_nc / f"{variable}_0p25.nc"
    if not source.is_file():
        return None
    target = paths.zarr / f"{variable}_0p25.zarr"
    target.parent.mkdir(parents=True, exist_ok=True)
    xr.open_dataset(source).chunk({"time": 12}).to_zarr(target, mode="w")
    return target
