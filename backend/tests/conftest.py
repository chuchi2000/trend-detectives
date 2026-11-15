"""Configuración común de las pruebas: servicio en modo DEMO con límites de prueba."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from app.core.config import PROJECT_ROOT, Settings
from app.services.atlas import AtlasService, build_service

FIXTURES = Path(__file__).parent / "fixtures"


def _square(west: float, south: float, east: float, north: float) -> dict:
    ring = [[west, south], [east, south], [east, north], [west, north], [west, south]]
    return {"type": "Polygon", "coordinates": [ring]}


@pytest.fixture()
def boundaries_dir(tmp_path: Path) -> Path:
    """Límites FICTICIOS (cuadrados) solo para probar la lógica de regiones."""
    folder = tmp_path / "boundaries"
    (folder / "municipalities").mkdir(parents=True)
    states = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"code": "09", "name": "Estado de prueba centro"},
                "geometry": _square(-100.0, 18.5, -98.0, 20.5),
            },
            {
                "type": "Feature",
                "properties": {"code": "26", "name": "Estado de prueba norte"},
                "geometry": _square(-112.0, 27.0, -109.0, 31.0),
            },
        ],
    }
    (folder / "states.geojson").write_text(json.dumps(states), encoding="utf-8")
    munis = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"code": "09015", "name": "Municipio pequeño"},
                "geometry": _square(-99.2, 19.4, -99.1, 19.5),
            },
        ],
    }
    (folder / "municipalities" / "09.geojson").write_text(json.dumps(munis), encoding="utf-8")
    return folder


@pytest.fixture()
def demo_service(tmp_path: Path, boundaries_dir: Path) -> AtlasService:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    shutil.move(str(boundaries_dir), data_dir / "boundaries")
    settings = Settings(data_mode="demo", data_dir=data_dir, metadata_dir=PROJECT_ROOT / "metadata")
    return build_service(settings)


@pytest.fixture()
def demo_service_without_boundaries(tmp_path: Path) -> AtlasService:
    settings = Settings(data_mode="demo", data_dir=tmp_path, metadata_dir=PROJECT_ROOT / "metadata")
    return build_service(settings)
