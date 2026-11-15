"""Malla común de 0.25° sobre México.

Filas de norte a sur (fila 0 = la más al norte) y columnas de oeste a este,
igual que una imagen. Esta malla se usa para comparaciones entre variables,
series de tiempo y estadísticas regionales.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class CommonGrid:
    west: float
    south: float
    east: float
    north: float
    res: float
    lons: np.ndarray = field(repr=False)
    lats: np.ndarray = field(repr=False)

    @classmethod
    def from_bounds(cls, bounds: list[float] | tuple[float, ...], res: float) -> CommonGrid:
        west, south, east, north = (float(b) for b in bounds)
        nx = round((east - west) / res)
        ny = round((north - south) / res)
        lons = west + res * (np.arange(nx) + 0.5)
        lats = north - res * (np.arange(ny) + 0.5)
        return cls(west, south, east, north, res, lons, lats)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.lats.size, self.lons.size)

    @property
    def lon2d(self) -> np.ndarray:
        return np.broadcast_to(self.lons[None, :], self.shape)

    @property
    def lat2d(self) -> np.ndarray:
        return np.broadcast_to(self.lats[:, None], self.shape)

    @property
    def area_weights(self) -> np.ndarray:
        """Peso proporcional al área de cada celda (cos de la latitud)."""
        return np.broadcast_to(np.cos(np.deg2rad(self.lats))[:, None], self.shape)

    def contains(self, lat: float, lon: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lon <= self.east

    def index_of(self, lat: float, lon: float) -> tuple[int, int]:
        row = int(np.clip((self.north - lat) // self.res, 0, self.shape[0] - 1))
        col = int(np.clip((lon - self.west) // self.res, 0, self.shape[1] - 1))
        return row, col

    def cell_center(self, row: int, col: int) -> tuple[float, float]:
        return float(self.lats[row]), float(self.lons[col])
