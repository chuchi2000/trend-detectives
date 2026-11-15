"""Fuente de datos de DEMOSTRACIÓN.

Genera campos SIMULADOS con patrones espaciales y estacionales plausibles para
poder desarrollar y probar la interfaz sin descargar datos de NASA.

Estos números NO son mediciones. Todas las respuestas en este modo llevan
"mode": "demo" y el frontend muestra un aviso permanente.

Los campos son deterministas: el mismo mes siempre produce los mismos valores,
así las pruebas son reproducibles.
"""

from __future__ import annotations

import zlib
from functools import cached_property
from typing import Any, Literal

import numpy as np

from app.services.dates import format_ym, from_index, iter_months, parse_ym, ym_index
from app.services.demo_geometry import MEXICO_APPROX_GEOMETRY
from app.services.geometry import points_in_geometry
from app.services.grid import CommonGrid
from app.services.products import ProductCatalog

DEMO_NOTE = "Valores SIMULADOS para desarrollo de la interfaz. No son mediciones de NASA."

# Ciudades usadas para simular focos de NO₂ (lon, lat, intensidad, radio en grados).
_NO2_SOURCES = [
    (-99.13, 19.43, 9.0, 0.45),
    (-100.31, 25.67, 4.5, 0.4),
    (-103.35, 20.67, 4.0, 0.38),
    (-98.2, 19.04, 2.5, 0.3),
    (-99.66, 19.29, 2.2, 0.28),
    (-99.34, 20.05, 3.0, 0.28),
    (-117.03, 32.5, 2.4, 0.32),
    (-106.44, 31.69, 2.0, 0.3),
    (-100.39, 20.59, 1.8, 0.3),
    (-101.68, 21.12, 1.8, 0.3),
    (-115.45, 32.62, 1.6, 0.3),
    (-110.95, 29.07, 1.0, 0.3),
]

# Factores estacionales por mes (enero..diciembre).
_PRECIP_SEASON = np.array([0.15, 0.12, 0.10, 0.12, 0.35, 0.80, 1.00, 1.00, 1.00, 0.60, 0.25, 0.18])
_ET_SEASON = np.array([0.35, 0.30, 0.30, 0.35, 0.45, 0.70, 0.95, 1.00, 1.00, 0.85, 0.60, 0.45])


def _bump(lon: np.ndarray, lat: np.ndarray, clon: float, clat: float, s: float) -> np.ndarray:
    return np.exp(-(((lon - clon) ** 2) + ((lat - clat) ** 2)) / (2 * s * s))


class DemoStore:
    mode: Literal["demo", "real"] = "demo"

    def __init__(self, products: ProductCatalog, grid: CommonGrid) -> None:
        self.products = products
        self.grid = grid
        self._cubes: dict[str, tuple[int, np.ndarray]] = {}

    # -- geometría ---------------------------------------------------------
    @cached_property
    def _mask(self) -> np.ndarray:
        inside = points_in_geometry(
            MEXICO_APPROX_GEOMETRY, self.grid.lon2d.ravel(), self.grid.lat2d.ravel()
        )
        return inside.reshape(self.grid.shape)

    def national_mask(self) -> np.ndarray:
        return self._mask

    def processed_months(self, variable: str) -> list[str] | None:
        return None

    # -- campos base -------------------------------------------------------
    @cached_property
    def _bases(self) -> dict[str, np.ndarray]:
        lon, lat = self.grid.lon2d, self.grid.lat2d
        east = (lon + 118.0) / 32.0
        precip = (
            0.08
            + 0.50 * np.exp(-(((lat - 17.0) / 5.0) ** 2)) * (0.5 + 0.5 * east)
            + 0.50 * _bump(lon, lat, -93.2, 17.3, 1.9)
            + 0.18 * _bump(lon, lat, -96.8, 19.6, 1.0)
            + 0.16 * _bump(lon, lat, -105.4, 23.0, 1.5)
            + 0.12 * _bump(lon, lat, -103.5, 19.2, 1.2)
        )
        no2 = 0.6 + sum(w * _bump(lon, lat, x, y, s) for x, y, w, s in _NO2_SOURCES)
        et = (
            0.08
            + 0.88 * np.exp(-(((lat - 17.0) / 4.8) ** 2)) * (0.45 + 0.55 * east)
            + 0.22 * _bump(lon, lat, -106.2, 24.5, 1.7)
            + 0.10 * _bump(lon, lat, -89.0, 20.5, 1.5)
            - 0.12 * _bump(lon, lat, -101.0, 21.0, 1.6)
        )
        heat = (
            0.30
            + 0.48 * (lat - 14.5) / 18.0
            + 0.18 * (1 - east)
            - 0.38 * _bump(lon, lat, -100.3, 20.3, 2.2)
            - 0.15 * _bump(lon, lat, -106.3, 25.5, 1.3)
            - 0.18 * np.exp(-(((lat - 16.5) / 2.5) ** 2)) * east
        )
        return {
            "precipitation": np.clip(precip, 0.02, 1.0),
            "no2": np.asarray(no2),
            "evapotranspiration": np.clip(et, 0.03, 1.0),
            "temperature": np.clip(heat, 0.0, 1.0),
        }

    def _month_field(self, variable: str, year: int, month: int) -> np.ndarray:
        base = self._bases[variable]
        # Semillas estables (crc32) para que los valores no cambien entre ejecuciones.
        rng = np.random.default_rng(zlib.crc32(f"{variable}-{year}-{month}".encode()))
        # Anomalía del año (igual para todo el país) + ruido por celda.
        year_rng = np.random.default_rng(zlib.crc32(f"{variable}-{year}".encode()))
        year_anomaly = year_rng.normal(0.0, 1.0)
        noise = rng.normal(0.0, 1.0, size=self.grid.shape)
        lat = self.grid.lat2d
        m = month - 1
        if variable == "precipitation":
            value = (
                380.0 * base * _PRECIP_SEASON[m] * (1 + 0.12 * year_anomaly) * (1 + 0.10 * noise)
            )
            value = np.clip(value, 0.0, None)
        elif variable == "no2":
            seasonal = 1.0 + 0.18 * np.cos(2 * np.pi * m / 12.0)
            value = 1e15 * base * seasonal * (1 + 0.05 * year_anomaly) * (1 + 0.06 * noise)
        elif variable == "evapotranspiration":
            value = 140.0 * base * _ET_SEASON[m] * (1 + 0.08 * year_anomaly) * (1 + 0.08 * noise)
            value = np.clip(value, 0.0, None)
        else:
            amplitude = 4.0 + 6.0 * np.clip((lat - 14.5) / 18.0, 0, 1)
            value = (
                16.0
                + 26.0 * base
                + amplitude * np.cos(2 * np.pi * (m - 4) / 12.0)
                + 0.6 * year_anomaly
                + 0.8 * noise
            )
        return np.where(self._mask, value, np.nan).astype("float32")

    def _variable_cube(self, variable: str) -> tuple[int, np.ndarray]:
        if variable not in self._cubes:
            start, end = self.products.availability(variable)
            months = list(iter_months(start, end))
            cube = np.stack([self._month_field(variable, y, m) for y, m in months])
            self._cubes[variable] = (ym_index(*parse_ym(start)), cube)
        return self._cubes[variable]

    # -- interfaz DataStore -------------------------------------------------
    def field(self, variable: str, year: int, month: int) -> np.ndarray:
        self.products.require_available(variable, year, month)
        first, cube = self._variable_cube(variable)
        return cube[ym_index(year, month) - first]

    def cube(self, variable: str, start: str, end: str) -> tuple[list[str], np.ndarray]:
        first, cube = self._variable_cube(variable)
        avail_start, avail_end = self.products.availability(variable)
        i0 = max(ym_index(*parse_ym(start)), ym_index(*parse_ym(avail_start)))
        i1 = min(ym_index(*parse_ym(end)), ym_index(*parse_ym(avail_end)))
        if i0 > i1:
            return [], np.empty((0, *self.grid.shape), dtype="float32")
        dates = [format_ym(*from_index(i)) for i in range(i0, i1 + 1)]
        return dates, cube[i0 - first : i1 - first + 1]

    def map_layer(self, variable: str, year: int, month: int) -> dict[str, Any]:
        values = self.field(variable, year, month)
        display = self.products.get(variable)["display"]
        scaled = values / float(display.get("scale", 1))
        flat = [None if not np.isfinite(v) else round(float(v), 3) for v in scaled.ravel()]
        n_mask = int(self._mask.sum())
        n_valid = int(np.isfinite(values).sum())
        return {
            "layer": {
                "kind": "grid",
                "grid": {
                    "west": self.grid.west,
                    "south": self.grid.south,
                    "east": self.grid.east,
                    "north": self.grid.north,
                    "res": self.grid.res,
                    "nx": self.grid.shape[1],
                    "ny": self.grid.shape[0],
                    "values": flat,
                },
                "attribution": "Datos simulados (DEMO)",
            },
            "resolution": f"{self.grid.res}° (malla común de demostración)",
            "quality": {
                "coverage": n_valid / n_mask if n_mask else 0.0,
                "n_valid": n_valid,
                "flags": ["demo"],
                "notes": [DEMO_NOTE],
            },
        }

    def point_value(
        self, variable: str, year: int, month: int, lat: float, lon: float
    ) -> dict[str, Any]:
        values = self.field(variable, year, month)
        row, col = self.grid.index_of(lat, lon)
        value = values[row, col]
        clat, clon = self.grid.cell_center(row, col)
        return {
            "value": None if not np.isfinite(value) else float(value),
            "cell": {"lat": clat, "lon": clon, "res": self.grid.res},
            "resolution": f"{self.grid.res}°",
        }
