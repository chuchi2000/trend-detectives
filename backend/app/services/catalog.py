"""Catálogo (índice) de archivos procesados.

Cada vez que un script de procesamiento genera un archivo, registra aquí una
entrada que dice qué variable, fecha, nivel y versión contiene. La API busca
en este índice en lugar de recorrer carpetas.

Niveles:
- "native": un COG mensual en la resolución original del producto (para el
  mapa y las consultas por punto).
- "comparative": el cubo de la malla común de 0.25° (series, estadísticas,
  correlaciones). Hay una sola entrada por variable que cubre todos los meses.

El índice es un archivo JSON. Más adelante puede migrarse a una tabla en
PostgreSQL/PostGIS sin cambiar la interfaz de esta clase.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

Level = Literal["native", "comparative"]


class CatalogEntry(BaseModel):
    variable: str
    level: Level
    date: str | None = Field(default=None, description="AAAA-MM; None en el cubo comparativo")
    product: str
    version: str
    path: str = Field(description="Ruta relativa a la carpeta data/")
    format: Literal["cog", "netcdf", "zarr"]
    units: str
    resolution_deg: float
    crs: str = "EPSG:4326"
    start: str | None = None
    end: str | None = None
    n_valid: int | None = None
    coverage: float | None = None
    quality: dict[str, Any] = Field(default_factory=dict)
    created: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))

    @property
    def key(self) -> tuple[str, str, str | None]:
        return (self.variable, self.level, self.date)


class Catalog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._entries: dict[tuple[str, str, str | None], CatalogEntry] = {}
        self._mtime: float | None = None
        self.reload()

    def reload(self) -> None:
        self._entries.clear()
        if self.path.is_file():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            for item in data.get("entries", []):
                entry = CatalogEntry.model_validate(item)
                self._entries[entry.key] = entry
            self._mtime = self.path.stat().st_mtime

    def refresh_if_changed(self) -> None:
        if self.path.is_file() and self.path.stat().st_mtime != self._mtime:
            self.reload()

    def add(self, entry: CatalogEntry) -> None:
        self._entries[entry.key] = entry

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "entries": [
                e.model_dump()
                for e in sorted(
                    self._entries.values(), key=lambda e: (e.variable, e.level, e.date or "")
                )
            ],
        }
        # Escritura atómica: primero a un archivo temporal y luego se renombra.
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)
        self._mtime = self.path.stat().st_mtime

    def find(self, variable: str, level: Level, date: str | None = None) -> CatalogEntry | None:
        return self._entries.get((variable, level, date))

    def processed_months(self, variable: str) -> list[str]:
        return sorted(
            e.date
            for e in self._entries.values()
            if e.variable == variable and e.level == "native" and e.date is not None
        )

    def entries(self) -> list[CatalogEntry]:
        return list(self._entries.values())
