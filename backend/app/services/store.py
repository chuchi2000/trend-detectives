"""Interfaz común de las fuentes de datos (DEMO o DATOS REALES).

La API trabaja contra esta interfaz; no sabe si los números vienen de un
generador de demostración o de los archivos procesados de NASA. Para agregar
otra fuente (por ejemplo, una base PostGIS) basta con implementar estos métodos.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol

import numpy as np

from app.services.grid import CommonGrid


class DataStore(Protocol):
    mode: Literal["demo", "real"]
    grid: CommonGrid

    def field(self, variable: str, year: int, month: int) -> np.ndarray:
        """Campo mensual en la malla común (unidades de la variable, NaN = sin dato)."""

    def cube(self, variable: str, start: str, end: str) -> tuple[list[str], np.ndarray]:
        """Serie de campos mensuales [tiempo, fila, columna] entre dos fechas AAAA-MM."""

    def map_layer(self, variable: str, year: int, month: int) -> dict[str, Any]:
        """Referencia a la capa del mapa: malla (DEMO) o teselas de TiTiler (REALES)."""

    def point_value(
        self, variable: str, year: int, month: int, lat: float, lon: float
    ) -> dict[str, Any]:
        """Valor en una coordenada, con la resolución a la que se leyó."""

    def national_mask(self) -> np.ndarray:
        """Celdas de la malla común que pertenecen a México."""

    def processed_months(self, variable: str) -> list[str] | None:
        """Meses procesados (None si la fuente genera cualquier mes disponible)."""
