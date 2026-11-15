"""Escritura de resultados: NetCDF (registro científico) y COG (para el mapa web).

- NetCDF mensual en data/processed/monthly/<variable>/: valor + capas de calidad
  + atributos de procedencia (producto, versión, método, fecha de proceso).
- COG en data/optimized/cog/<variable>/: una banda float32, NaN como "sin dato",
  compresión DEFLATE y pirámides internas para que TiTiler sirva teselas rápido.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np


def grid_coords(
    west: float, north: float, res_x: float, res_y: float, nx: int, ny: int
) -> tuple[np.ndarray, np.ndarray]:
    lons = west + res_x * (np.arange(nx) + 0.5)
    lats = north - res_y * (np.arange(ny) + 0.5)
    return lats, lons


def write_cog(
    path: Path, data: np.ndarray, west: float, north: float, res_x: float, res_y: float
) -> Path:
    import rasterio
    from rasterio.transform import from_origin

    path.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "COG",
        "height": data.shape[0],
        "width": data.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:4326",
        "transform": from_origin(west, north, res_x, res_y),
        "nodata": float("nan"),
        "compress": "DEFLATE",
        "predictor": "YES",
        "blocksize": 512,
        "overview_resampling": "average",
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data.astype("float32"), 1)
    return path


def write_monthly_netcdf(
    path: Path,
    variable: str,
    values: np.ndarray,
    lats: np.ndarray,
    lons: np.ndarray,
    year: int,
    month: int,
    units: str,
    attrs: dict[str, Any],
    quality_layers: dict[str, tuple[np.ndarray, str]] | None = None,
) -> Path:
    import xarray as xr

    path.parent.mkdir(parents=True, exist_ok=True)
    time = np.array([np.datetime64(f"{year:04d}-{month:02d}-01")])
    data_vars: dict[str, Any] = {
        variable: (("time", "lat", "lon"), values[None].astype("float32"), {"units": units}),
    }
    for name, (layer, layer_units) in (quality_layers or {}).items():
        data_vars[name] = (
            ("time", "lat", "lon"),
            layer[None].astype("float32"),
            {"units": layer_units},
        )
    ds = xr.Dataset(
        data_vars,
        coords={
            "time": time,
            "lat": ("lat", lats, {"units": "degrees_north"}),
            "lon": ("lon", lons, {"units": "degrees_east"}),
        },
        attrs={
            **attrs,
            "title": f"Atlas Ambiental de México — {variable} {year:04d}-{month:02d}",
            "history": f"{datetime.now(UTC).isoformat(timespec='seconds')} procesado por Atlas Ambiental de México",
            "Conventions": "CF-1.8",
        },
    )
    encoding = {
        name: {"zlib": True, "complevel": 4, "_FillValue": np.float32("nan")} for name in data_vars
    }
    ds.to_netcdf(path, encoding=encoding)
    return path


def valid_summary(values: np.ndarray, mask: np.ndarray | None = None) -> tuple[int, float]:
    region = np.ones(values.shape, dtype=bool) if mask is None else mask
    total = int(region.sum())
    n_valid = int((np.isfinite(values) & region).sum())
    return n_valid, (n_valid / total if total else 0.0)
