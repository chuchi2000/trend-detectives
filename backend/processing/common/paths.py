"""Rutas de la carpeta data/ y área de México usadas por el procesamiento."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.services.catalog import Catalog
from app.services.products import ProductCatalog

# Caja de México con un margen de una celda de 0.25° (oeste, sur, este, norte).
MEXICO_BBOX = (-118.75, 14.25, -86.25, 33.25)


@dataclass(frozen=True)
class DataPaths:
    root: Path

    def raw(self, variable: str) -> Path:
        return self.root / "raw" / variable

    def processed_monthly(self, variable: str) -> Path:
        return self.root / "processed" / "monthly" / variable

    def cog(self, variable: str) -> Path:
        return self.root / "optimized" / "cog" / variable

    @property
    def comparative_nc(self) -> Path:
        return self.root / "processed" / "comparative"

    @property
    def zarr(self) -> Path:
        return self.root / "optimized" / "zarr"

    @property
    def boundaries(self) -> Path:
        return self.root / "boundaries"

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root.resolve()).as_posix()


def context() -> tuple[DataPaths, ProductCatalog, Catalog]:
    settings = get_settings()
    return (
        DataPaths(settings.data_dir),
        ProductCatalog.from_file(settings.products_file),
        Catalog(settings.catalog_file),
    )
