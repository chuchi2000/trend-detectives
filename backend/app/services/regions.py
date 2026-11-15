"""Límites estatales y municipales (INEGI, Marco Geoestadístico).

Los archivos los genera `python -m processing.cli limites` (servicio web del INEGI
o, con --origen, sus shapefiles) y quedan en data/boundaries/:

- states.geojson                     32 entidades (propiedades: code, name)
- municipalities/<CVE_ENT>.geojson   municipios de cada entidad (code, name, state_code)
- mexico.geojson                     contorno nacional (para máscaras)

Si los archivos no existen, el servicio responde que los límites no están
cargados en lugar de fallar.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from app.core.errors import InvalidRequest, NotFound
from app.core.i18n import tr
from app.services.geometry import points_in_geometry
from app.services.grid import CommonGrid


def missing_message() -> str:
    return tr(
        "Los límites del INEGI todavía no están cargados. En la carpeta backend ejecuta "
        "`python -m processing.cli limites` (los descarga del INEGI) y reinicia la API.",
        "The INEGI boundaries are not loaded yet. In the backend folder run "
        "`python -m processing.cli limites` (it downloads them from INEGI) and restart the API.",
    )


def parse_region(text: str | None) -> tuple[str, str | None]:
    """'nacional' | 'estado:24' | 'municipio:24028' -> (nivel, clave)."""
    if not text or text == "nacional":
        return "national", None
    level, _, code = text.partition(":")
    mapping = {"estado": "state", "municipio": "municipality"}
    if level not in mapping or not code.isdigit():
        raise InvalidRequest(
            tr(
                "Región inválida. Usa 'nacional', 'estado:CLAVE' o 'municipio:CLAVE'.",
                "Invalid region. Use 'nacional', 'estado:CODE' or 'municipio:CODE'.",
            )
        )
    return mapping[level], code


class RegionService:
    def __init__(self, boundaries_dir: Path, grid: CommonGrid) -> None:
        self.dir = boundaries_dir
        self.grid = grid
        self._mask_cache: dict[tuple[str, str | None], np.ndarray] = {}

    @property
    def available(self) -> bool:
        return (self.dir / "states.geojson").is_file()

    def _load(self, relative: str) -> dict[str, Any]:
        return _read_geojson(str(self.dir / relative))

    def states(self) -> list[dict[str, Any]]:
        if not self.available:
            return []
        return sorted(
            (
                {"level": "state", "code": f["properties"]["code"], "name": f["properties"]["name"]}
                for f in self._load("states.geojson")["features"]
            ),
            key=lambda r: r["code"],
        )

    def municipalities(self, state_code: str) -> list[dict[str, Any]]:
        path = self.dir / "municipalities" / f"{state_code}.geojson"
        if not path.is_file():
            return []
        return sorted(
            (
                {
                    "level": "municipality",
                    "code": f["properties"]["code"],
                    "name": f["properties"]["name"],
                    "state_code": state_code,
                }
                for f in self._load(f"municipalities/{state_code}.geojson")["features"]
            ),
            key=lambda r: r["code"],
        )

    def geojson(self, level: str, state_code: str | None = None) -> dict[str, Any]:
        if level == "state":
            if not self.available:
                raise NotFound(missing_message(), code="limites_no_cargados")
            return self._load("states.geojson")
        if level == "municipality":
            if not state_code:
                raise InvalidRequest(
                    tr(
                        "Para municipios indica la entidad con el parámetro 'estado'.",
                        "For municipalities, give the state with the 'estado' parameter.",
                    )
                )
            path = self.dir / "municipalities" / f"{state_code}.geojson"
            if not path.is_file():
                raise NotFound(missing_message(), code="limites_no_cargados")
            return self._load(f"municipalities/{state_code}.geojson")
        raise InvalidRequest(
            tr(
                "Nivel inválido: usa 'state' o 'municipality'.",
                "Invalid level: use 'state' or 'municipality'.",
            )
        )

    def feature(self, level: str, code: str) -> dict[str, Any]:
        collection = self.geojson(level, code[:2] if level == "municipality" else None)
        for feature in collection["features"]:
            if feature["properties"]["code"] == code:
                return feature
        raise NotFound(tr(f"No se encontró la región {code}.", f"Region {code} was not found."))

    def name_of(self, level: str, code: str | None) -> str:
        if level == "national":
            return tr("México (todo el país)", "Mexico (whole country)")
        assert code is not None
        return str(self.feature(level, code)["properties"]["name"])

    def mask(self, level: str, code: str | None, fallback_national: np.ndarray) -> np.ndarray:
        """Celdas de la malla común cuyo centro cae dentro de la región."""
        if level == "national":
            return fallback_national
        key = (level, code)
        if key not in self._mask_cache:
            assert code is not None
            geometry = self.feature(level, code)["geometry"]
            inside = points_in_geometry(geometry, self.grid.lon2d.ravel(), self.grid.lat2d.ravel())
            mask = inside.reshape(self.grid.shape)
            if not mask.any():
                # Regiones más pequeñas que una celda de 0.25°: se usa la celda de su centroide.
                lon_c, lat_c = _centroid(geometry)
                row, col = self.grid.index_of(lat_c, lon_c)
                mask = np.zeros(self.grid.shape, dtype=bool)
                mask[row, col] = True
            self._mask_cache[key] = mask
        return self._mask_cache[key]

    def national_geometry(self) -> dict[str, Any] | None:
        """Contorno de México (GeoJSON, lon/lat) o None si los límites no están cargados."""
        path = self.dir / "mexico.geojson"
        if not path.is_file():
            return None
        data = _read_geojson(str(path))
        return data["features"][0]["geometry"] if data.get("type") == "FeatureCollection" else data

    def national_mask(self) -> np.ndarray | None:
        if ("national", None) not in self._mask_cache:
            geometry = self.national_geometry()
            if geometry is None:
                return None
            inside = points_in_geometry(geometry, self.grid.lon2d.ravel(), self.grid.lat2d.ravel())
            self._mask_cache[("national", None)] = inside.reshape(self.grid.shape)
        return self._mask_cache[("national", None)]


def _centroid(geometry: dict[str, Any]) -> tuple[float, float]:
    polygons = (
        geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    )
    pts = np.vstack([np.asarray(p[0], dtype=float) for p in polygons])
    return float(pts[:, 0].mean()), float(pts[:, 1].mean())


@lru_cache(maxsize=64)
def _read_geojson(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
