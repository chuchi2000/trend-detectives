"""Límites estatales y municipales a partir del Marco Geoestadístico del INEGI.

Entrada: los shapefiles del INEGI (https://www.inegi.org.mx/temas/mg/),
descomprimidos en data/boundaries/inegi/ con los archivos `00ent.shp`
(entidades) y `00mun.shp` (municipios).

Salida:
  data/boundaries/states.geojson                 32 entidades
  data/boundaries/municipalities/<CVE_ENT>.geojson
  data/boundaries/mexico.geojson                 contorno nacional

Las geometrías se simplifican para el navegador (tolerancia en grados); la
versión sin simplificar se conserva en el shapefile original.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from processing.common.paths import context

logger = logging.getLogger("atlas.boundaries")
STATE_FIELDS = ("CVEGEO", "CVE_ENT", "NOMGEO", "NOM_ENT")
MUNI_FIELDS = ("CVEGEO", "CVE_MUN", "NOMGEO", "NOM_MUN")


def _first(row: Any, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in row and row[name] is not None:
            return str(row[name])
    return None


def build(source_dir: Path | None = None, tolerance: float = 0.005) -> dict[str, Path]:
    import geopandas as gpd

    paths, _, _ = context()
    src = source_dir or (paths.boundaries / "inegi")
    states_shp = next(iter(src.rglob("*ent.shp")), None)
    munis_shp = next(iter(src.rglob("*mun.shp")), None)
    if states_shp is None:
        raise FileNotFoundError(
            f"No se encontró el shapefile de entidades en {src}. Descarga el Marco Geoestadístico "
            "del INEGI y descomprímelo ahí (ver docs/05-procesamiento-nasa.md)."
        )

    written: dict[str, Path] = {}
    states = gpd.read_file(states_shp).to_crs("EPSG:4326")
    states["code"] = states.apply(lambda r: (_first(r, STATE_FIELDS) or "")[:2], axis=1)
    states["name"] = states.apply(lambda r: _first(r, ("NOMGEO", "NOM_ENT")) or "", axis=1)
    simple = states[["code", "name", "geometry"]].copy()
    simple["geometry"] = simple.geometry.simplify(tolerance, preserve_topology=True)
    out = paths.boundaries / "states.geojson"
    simple.to_file(out, driver="GeoJSON")
    written["states"] = out

    national = simple.dissolve().simplify(tolerance * 2, preserve_topology=True)
    (paths.boundaries / "mexico.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": "México"},
                        "geometry": json.loads(national.to_json())["features"][0]["geometry"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    written["mexico"] = paths.boundaries / "mexico.geojson"

    if munis_shp is not None:
        munis = gpd.read_file(munis_shp).to_crs("EPSG:4326")
        munis["code"] = munis.apply(lambda r: (_first(r, ("CVEGEO",)) or "")[:5], axis=1)
        munis["name"] = munis.apply(lambda r: _first(r, ("NOMGEO", "NOM_MUN")) or "", axis=1)
        munis["state_code"] = munis["code"].str[:2]
        munis["geometry"] = munis.geometry.simplify(tolerance, preserve_topology=True)
        folder = paths.boundaries / "municipalities"
        folder.mkdir(parents=True, exist_ok=True)
        for state_code, group in munis.groupby("state_code"):
            path = folder / f"{state_code}.geojson"
            group[["code", "name", "state_code", "geometry"]].to_file(path, driver="GeoJSON")
        written["municipalities"] = folder
        logger.info("Municipios escritos para %d entidades.", munis["state_code"].nunique())
    else:
        logger.warning("No se encontró el shapefile de municipios; solo se generaron entidades.")
    logger.info("Límites listos en %s", paths.boundaries)
    return written
