"""Catálogo de productos NASA auditados (metadata/sources/products.json).

Es la fuente única de verdad sobre cada variable: producto, versión,
disponibilidad, unidades, escalas de color y advertencias. El frontend lee el
mismo archivo, así que un cambio aquí se refleja en ambos lados.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.errors import DateUnavailable, NotFound
from app.services.dates import format_ym, human_ym, parse_ym, ym_index

VARIABLE_IDS = ("precipitation", "no2", "evapotranspiration", "temperature")


class ProductCatalog:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        self._variables: dict[str, dict[str, Any]] = data["variables"]

    @classmethod
    def from_file(cls, path: Path) -> ProductCatalog:
        return cls(json.loads(path.read_text(encoding="utf-8")))

    # -- consultas ---------------------------------------------------------
    @property
    def raw(self) -> dict[str, Any]:
        return self._data

    @property
    def variable_ids(self) -> list[str]:
        return sorted(self._variables, key=lambda v: self._variables[v]["order"])

    def get(self, variable: str) -> dict[str, Any]:
        try:
            return self._variables[variable]
        except KeyError as exc:
            valid = ", ".join(self.variable_ids)
            raise NotFound(f"Variable '{variable}' desconocida. Usa una de: {valid}.") from exc

    def availability(self, variable: str) -> tuple[str, str]:
        temporal = self.get(variable)["temporal"]
        return temporal["available_start"], temporal["available_end"]

    @property
    def common_grid(self) -> dict[str, Any]:
        return self._data["common_grid"]

    @property
    def comparison_period(self) -> tuple[str, str]:
        period = self._data["comparison_period"]
        return period["start"], period["end"]

    @property
    def study_period(self) -> tuple[str, str]:
        period = self._data["study_period"]
        return period["start"], period["end"]

    # -- validación --------------------------------------------------------
    def is_available(self, variable: str, year: int, month: int) -> bool:
        start, end = self.availability(variable)
        i = ym_index(year, month)
        return ym_index(*parse_ym(start)) <= i <= ym_index(*parse_ym(end))

    def require_available(self, variable: str, year: int, month: int) -> None:
        if self.is_available(variable, year, month):
            return
        start, end = self.availability(variable)
        name = self.get(variable)["name"]
        raise DateUnavailable(
            f"{name} no tiene datos para {human_ym(format_ym(year, month))}. "
            f"Hay datos de {human_ym(start)} a {human_ym(end)}."
        )

    def common_available_range(self, variables: list[str]) -> tuple[str, str] | None:
        starts = [ym_index(*parse_ym(self.availability(v)[0])) for v in variables]
        ends = [ym_index(*parse_ym(self.availability(v)[1])) for v in variables]
        i0, i1 = max(starts), min(ends)
        if i0 > i1:
            return None
        return format_ym(i0 // 12, i0 % 12 + 1), format_ym(i1 // 12, i1 % 12 + 1)


@lru_cache
def load_products(path: str) -> ProductCatalog:
    return ProductCatalog.from_file(Path(path))
