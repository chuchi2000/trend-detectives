"""Límites desde el servicio web del INEGI, con respuestas simuladas.

Las respuestas imitan el formato observado del servicio (FeatureCollection con
`metadatos`, `crs` EPSG:6365, propiedades en minúsculas y como texto).
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from app.services.grid import CommonGrid
from app.services.regions import RegionService
from processing.boundaries import inegi_service as svc


def _wavy_square(x0: float, y0: float, size: float, n: int = 400) -> list[list[float]]:
    """Cuadrado con un borde ondulado fino (mucho detalle que simplificar)."""
    pts = []
    for i in range(n):
        t = i / n
        pts.append([x0 + size * t, y0 + 0.0005 * math.sin(60 * math.pi * t)])
    pts += [[x0 + size, y0], [x0 + size, y0 + size], [x0, y0 + size], [x0, y0]]
    return pts


def _collection(features: list[dict]) -> dict:
    return {
        "type": "FeatureCollection",
        "metadatos": {"Fuente": "INEGI"},
        "crs": {"type": "name", "properties": {"name": "EPSG:6365"}},
        "totalReg": len(features),
        "features": features,
    }


STATES = {
    "09": ("Ciudad de México", -99.4, 19.0, 0.6),
    "24": ("San Luis Potosí", -101.5, 21.5, 2.0),
}


def fake_inegi(url: str) -> dict:
    kind, code = url.rsplit("/", 2)[-2:]
    name, x0, y0, size = STATES[code]
    if kind == "mgee":
        return _collection(
            [
                {
                    "type": "Feature",
                    "numReg": 1,
                    "properties": {
                        "cvegeo": code,
                        "cve_ent": code,
                        "nomgeo": name,
                        "pob_total": "1",
                    },
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [[_wavy_square(x0, y0, size)]],
                    },
                }
            ]
        )
    half = size / 2
    feats = []
    for k, (dx, dy) in enumerate([(0, 0), (half, 0), (0, half), (half, half)], start=1):
        feats.append(
            {
                "type": "Feature",
                "numReg": k,
                "properties": {
                    "cvegeo": f"{code}{k:03d}",
                    "cve_ent": code,
                    "cve_mun": f"{k:03d}",
                    "nomgeo": f"Municipio {k}",
                },
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [[_wavy_square(x0 + dx, y0 + dy, half, n=50)]],
                },
            }
        )
    # Un municipio diminuto, más pequeño que la tolerancia de simplificación.
    tiny = [
        [x0 + 0.01, y0 + 0.01],
        [x0 + 0.0105, y0 + 0.01],
        [x0 + 0.0105, y0 + 0.0105],
        [x0 + 0.01, y0 + 0.01],
    ]
    feats.append(
        {
            "type": "Feature",
            "properties": {"cvegeo": f"{code}099", "nomgeo": "Diminuto"},
            "geometry": {"type": "MultiPolygon", "coordinates": [[tiny]]},
        }
    )
    return _collection(feats)


def test_douglas_peucker_removes_detail_below_tolerance():
    line = np.array([[0, 0], [1, 0.001], [2, -0.001], [3, 0], [3, 3]], dtype=float)
    assert svc.douglas_peucker(line, 0.01).tolist() == [0, 3, 4]
    assert len(svc.douglas_peucker(line, 0.0)) == 5


def test_simplified_ring_stays_closed():
    ring = _wavy_square(-100, 20, 1)
    out = svc.simplify_ring(ring, 0.005)
    assert out is not None
    assert out[0] == out[-1]
    assert len(out) < len(ring) / 10


def test_build_writes_files_the_api_understands(tmp_path):
    calls: list[str] = []

    def fetch(url: str) -> dict:
        calls.append(url)
        return fake_inegi(url)

    svc.build(out_dir=tmp_path, fetch=fetch, states=["09", "24"], pause=0)
    assert len(calls) == 4

    states = json.loads((tmp_path / "states.geojson").read_text(encoding="utf-8"))
    assert [f["properties"] for f in states["features"]] == [
        {"code": "09", "name": "Ciudad de México"},
        {"code": "24", "name": "San Luis Potosí"},
    ]
    assert "crs" not in states  # GeoJSON estándar (RFC 7946)

    regions = RegionService(tmp_path, CommonGrid.from_bounds([-118.75, 14.25, -86.25, 33.25], 0.25))
    assert regions.available
    munis = regions.municipalities("24")
    assert [m["code"] for m in munis] == ["24001", "24002", "24003", "24004", "24099"]
    assert regions.name_of("state", "24") == "San Luis Potosí"
    # El estado de 2° × 2° contiene 8 × 8 celdas de 0.25°.
    assert regions.mask("state", "24", np.ones(regions.grid.shape, bool)).sum() == 64
    # El municipio diminuto se conserva (sin simplificar) y usa la celda de su centroide.
    assert regions.mask("municipality", "24099", np.ones(regions.grid.shape, bool)).sum() == 1
    assert regions.national_mask().sum() > 64


def test_build_resumes_from_local_copies(tmp_path):
    svc.build(out_dir=tmp_path, fetch=fake_inegi, states=["09"], pause=0)

    def offline(url: str) -> dict:
        raise AssertionError("no debería volver a descargar")

    svc.build(out_dir=tmp_path, fetch=offline, states=["09"], pause=0)


def test_unexpected_coordinates_are_rejected(tmp_path):
    def projected(url: str) -> dict:
        data = fake_inegi(url)
        for f in data["features"]:
            f["geometry"]["coordinates"] = [
                [[[x * 1e4, y * 1e4] for x, y in ring] for ring in poly]
                for poly in f["geometry"]["coordinates"]
            ]
        return data

    with pytest.raises(ValueError, match="no parecen longitud/latitud"):
        svc.build(out_dir=tmp_path, fetch=projected, states=["09"], pause=0)


def test_non_geojson_response_is_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="FeatureCollection"):
        svc.build(out_dir=tmp_path, fetch=lambda url: {"error": "x"}, states=["09"], pause=0)
