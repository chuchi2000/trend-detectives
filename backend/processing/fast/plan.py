"""Planeación sin dependencias externas: meses, mallas y división en solicitudes.

Todo lo que se puede decidir sin hablar con Google ni con NASA vive aquí, para
poder probarlo (tests/test_fast_plan.py).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from processing.common.temporal import composite_length, overlap_days

# Malla del mapa para MODIS en modo rápido. 0.025° (≈ 2.8 km) divide exacto la celda
# comparativa de 0.25° (10 × 10) y mantiene cada solicitud a Earth Engine en ~8 MB.
DEFAULT_MAP_RES = 0.025
MEXICO_WEST, MEXICO_SOUTH, MEXICO_EAST, MEXICO_NORTH = -118.75, 14.25, -86.25, 33.25

# Earth Engine limita cada solicitud a 48 MB sin comprimir; se deja margen.
MAX_REQUEST_BYTES = 40_000_000


@dataclass(frozen=True)
class Grid:
    """Malla regular en EPSG:4326, con el norte arriba."""

    west: float
    north: float
    res: float
    width: int
    height: int

    @property
    def south(self) -> float:
        return self.north - self.res * self.height

    @property
    def east(self) -> float:
        return self.west + self.res * self.width

    def tile_rows(self, n_bands: int, bytes_per_value: int = 4) -> list[tuple[int, int]]:
        """Filas (inicio, cantidad) de cada solicitud para no pasar el límite de tamaño."""
        per_row = self.width * n_bands * bytes_per_value
        rows = max(1, MAX_REQUEST_BYTES // per_row)
        return [(r0, min(rows, self.height - r0)) for r0 in range(0, self.height, rows)]

    def tiles(self, max_size: int | None, n_bands: int = 2) -> list[tuple[int, int, int, int]]:
        """Bloques (fila, n_filas, columna, n_columnas) de a lo más max_size × max_size.

        Earth Engine limita la memoria por solicitud: para MODIS, que se calcula en la
        resolución nativa antes de agregarse, conviene pedir bloques pequeños.
        Sin max_size, se usan franjas que respetan solo el límite de tamaño de respuesta.
        """
        if max_size is None:
            return [(r0, rows, 0, self.width) for r0, rows in self.tile_rows(n_bands)]
        return [
            (r0, min(max_size, self.height - r0), c0, min(max_size, self.width - c0))
            for r0 in range(0, self.height, max_size)
            for c0 in range(0, self.width, max_size)
        ]

    def affine(self, row_offset: int = 0, col_offset: int = 0) -> dict[str, float]:
        return {
            "scaleX": self.res,
            "shearX": 0.0,
            "translateX": self.west + col_offset * self.res,
            "shearY": 0.0,
            "scaleY": -self.res,
            "translateY": self.north - row_offset * self.res,
        }


def aligned_grid(res: float) -> Grid:
    """Malla que cubre México con bordes múltiplos de `res` (alineada con la malla global
    del producto, que empieza en −180° / −90°). Así no se remuestrea el producto nativo."""
    west = math.floor(round(MEXICO_WEST / res, 9)) * res
    east = math.ceil(round(MEXICO_EAST / res, 9)) * res
    south = math.floor(round(MEXICO_SOUTH / res, 9)) * res
    north = math.ceil(round(MEXICO_NORTH / res, 9)) * res
    return Grid(
        west=round(west, 9),
        north=round(north, 9),
        res=res,
        width=int(round((east - west) / res)),
        height=int(round((north - south) / res)),
    )


def months_between(start: str, end: str) -> list[tuple[int, int]]:
    y0, m0 = (int(x) for x in start.split("-"))
    y1, m1 = (int(x) for x in end.split("-"))
    out = []
    y, m = y0, m0
    while (y, m) <= (y1, m1):
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


@dataclass(frozen=True)
class CompositeUse:
    start: date
    days_in_month: int
    length: int


def composites_plan(starts: list[date], year: int, month: int) -> list[CompositeUse]:
    """Compuestos de 8 días que tocan el mes, con los días que aportan y su duración.

    Misma regla que el procesamiento clásico (processing/common/temporal.py): el
    último compuesto del año dura 5 o 6 días.
    """
    plan = []
    for start in sorted(starts):
        length = composite_length(start)
        days = overlap_days(start, length, year, month)
        if days > 0:
            plan.append(CompositeUse(start, days, length))
    return plan


def composite_search_window(year: int, month: int) -> tuple[date, date]:
    """Fechas para buscar compuestos: uno que empieza hasta 7 días antes puede tocar el mes."""
    first = date(year, month, 1) - timedelta(days=7)
    last = date(year + (month == 12), month % 12 + 1, 1)
    return first, last
