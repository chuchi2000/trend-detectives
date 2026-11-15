"""Límites estatales y municipales desde el servicio web del INEGI.

Es la forma recomendada de preparar los límites: no hay que descargar ni
descomprimir el Marco Geoestadístico y no necesita librerías extra (solo NumPy).

Servicio (documentado por el INEGI en
https://inegi.org.mx/servicios/descargas/Consulta_info_vectorial.pdf):

    https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgee/<CVE_ENT>   un estado
    https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/<CVE_ENT>   municipios de un estado

Responde GeoJSON con coordenadas geográficas en EPSG:6365 (marco de referencia
oficial de México, ITRF2008). Su diferencia con WGS 84 es de menos de un metro,
despreciable para un mapa nacional y para celdas de 0.25°, así que se usan tal cual.

Pasos:
1. Descarga 32 estados y los municipios de cada estado (64 peticiones). Cada
   respuesta se guarda en data/boundaries/inegi_servicio/; si el proceso se corta,
   al repetirlo solo descarga lo que falta.
2. Simplifica las líneas con Douglas–Peucker para que el navegador las cargue
   rápido (tolerancia en grados; 0.005° ≈ 500 m en estados, 0.002° ≈ 200 m en
   municipios). Islas más pequeñas que la tolerancia se omiten en la versión
   simplificada. Como cada polígono se simplifica por separado, entre vecinos
   pueden quedar huecos o traslapes de ese orden: es una capa de visualización.
3. Escribe los mismos archivos que el método con shapefiles:
   states.geojson, municipalities/<CVE_ENT>.geojson y mexico.geojson.
"""

from __future__ import annotations

import gzip
import http.client
import json
import logging
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("atlas.boundaries")

BASE_URL = "https://gaia.inegi.org.mx/wscatgeo/v2/geo"
STATE_CODES = [f"{i:02d}" for i in range(1, 33)]
# Recuadro amplio de México para detectar coordenadas en un sistema inesperado.
LON_RANGE = (-120.0, -85.0)
LAT_RANGE = (13.0, 34.0)

Fetcher = Callable[[str], dict[str, Any]]


# --------------------------------------------------------------------------- descarga
def _read_body(response: Any) -> bytes:
    body = response.read()
    if (response.headers.get("Content-Encoding") or "").lower() == "gzip":
        body = gzip.decompress(body)
    return body


def http_fetch(url: str, timeout: float = 180.0, retries: int = 5) -> dict[str, Any]:
    """GET con reintentos. Pide la respuesta comprimida (gzip) cuando el servidor la ofrece.

    El servidor del INEGI a veces corta la conexión a mitad de una respuesta grande
    (http.client.IncompleteRead); en ese caso se espera un poco y se repite.
    """
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AtlasAmbientalMexico/0.1",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(_read_body(response).decode("utf-8"))
        except (
            OSError,  # incluye URLError, TimeoutError y conexiones reiniciadas
            http.client.HTTPException,  # incluye IncompleteRead (respuesta cortada)
            ValueError,  # JSON incompleto, gzip dañado o texto no UTF-8
        ) as exc:
            last_error = exc
            wait = 3 * attempt
            logger.warning(
                "Descarga interrumpida (intento %d/%d): %s. Reintento en %d s.",
                attempt,
                retries,
                type(exc).__name__,
                wait,
            )
            if attempt < retries:
                time.sleep(wait)
    raise RuntimeError(
        f"No se pudo descargar {url} después de {retries} intentos ({type(last_error).__name__}). "
        "El servidor del INEGI puede estar saturado: espera unos minutos y vuelve a ejecutar el "
        "comando; lo ya descargado se conserva."
    )


def cached_fetch(url: str, cache_file: Path, fetch: Fetcher) -> tuple[dict[str, Any], bool]:
    """(datos, si_hubo_descarga). Usa la copia local si ya existe."""
    if cache_file.is_file():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8")), False
        except json.JSONDecodeError:
            logger.warning("Copia local dañada, se vuelve a descargar: %s", cache_file.name)
    data = fetch(url)
    if data.get("type") != "FeatureCollection" or not data.get("features"):
        raise RuntimeError(
            f"Respuesta inesperada del INEGI para {url}: no es un FeatureCollection."
        )
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(cache_file)
    return data, True


# ----------------------------------------------------------------------- simplificación
def douglas_peucker(points: np.ndarray, tolerance: float) -> np.ndarray:
    """Índices de los vértices que se conservan (algoritmo de Douglas–Peucker).

    Admite polilíneas cuyo primer y último punto coinciden (anillos cerrados):
    en ese caso la distancia se mide al punto, no a un segmento de longitud cero.
    """
    n = len(points)
    if n <= 2:
        return np.arange(n)
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        start, end = stack.pop()
        if end - start < 2:
            continue
        a, b = points[start], points[end]
        segment = points[start + 1 : end]
        ab = b - a
        length = float(np.hypot(ab[0], ab[1]))
        if length == 0.0:
            distances = np.hypot(segment[:, 0] - a[0], segment[:, 1] - a[1])
        else:
            distances = np.abs(ab[0] * (segment[:, 1] - a[1]) - ab[1] * (segment[:, 0] - a[0]))
            distances = distances / length
        index = int(np.argmax(distances))
        if distances[index] > tolerance:
            split = start + 1 + index
            keep[split] = True
            stack.append((start, split))
            stack.append((split, end))
    return np.flatnonzero(keep)


def simplify_ring(
    ring: list[list[float]], tolerance: float, decimals: int = 5
) -> list[list[float]] | None:
    """Anillo simplificado y redondeado, o None si se reduce a menos de un triángulo."""
    points = np.asarray(ring, dtype=float)[:, :2]
    if len(points) < 4:
        return None
    if not np.array_equal(points[0], points[-1]):
        points = np.vstack([points, points[:1]])
    kept = points[douglas_peucker(points, tolerance)] if tolerance > 0 else points
    kept = np.round(kept, decimals)
    # Quitar vértices repetidos consecutivos que aparecen al redondear.
    distinct = np.concatenate([[True], np.any(np.diff(kept, axis=0) != 0, axis=1)])
    kept = kept[distinct]
    if not np.array_equal(kept[0], kept[-1]):
        kept = np.vstack([kept, kept[:1]])
    if len(kept) < 4:
        return None
    return kept.tolist()


def _polygons_of(geometry: dict[str, Any]) -> list[list[list[list[float]]]]:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"]]
    if geometry["type"] == "MultiPolygon":
        return geometry["coordinates"]
    raise ValueError(f"Tipo de geometría no admitido: {geometry['type']}")


def _ring_area(ring: list[list[float]]) -> float:
    pts = np.asarray(ring, dtype=float)
    x, y = pts[:, 0], pts[:, 1]
    return float(abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2)


def simplify_geometry(geometry: dict[str, Any], tolerance: float) -> dict[str, Any]:
    polygons_out = []
    for polygon in _polygons_of(geometry):
        outer = simplify_ring(polygon[0], tolerance)
        if outer is None:
            continue
        holes = [h for h in (simplify_ring(r, tolerance) for r in polygon[1:]) if h is not None]
        polygons_out.append([outer, *holes])
    if not polygons_out:
        # Región más pequeña que la tolerancia: se conserva su polígono mayor sin simplificar.
        largest = max(_polygons_of(geometry), key=lambda p: _ring_area(p[0]))
        outer = simplify_ring(largest[0], 0.0)
        if outer is None:
            raise ValueError("Geometría degenerada (menos de tres vértices).")
        polygons_out = [[outer]]
    if len(polygons_out) == 1:
        return {"type": "Polygon", "coordinates": polygons_out[0]}
    return {"type": "MultiPolygon", "coordinates": polygons_out}


def _check_coordinates(geometry: dict[str, Any], label: str) -> None:
    pts = np.vstack([np.asarray(p[0], dtype=float)[:, :2] for p in _polygons_of(geometry)])
    lon_ok = LON_RANGE[0] <= pts[:, 0].min() and pts[:, 0].max() <= LON_RANGE[1]
    lat_ok = LAT_RANGE[0] <= pts[:, 1].min() and pts[:, 1].max() <= LAT_RANGE[1]
    if not (lon_ok and lat_ok):
        raise ValueError(
            f"Las coordenadas de {label} no parecen longitud/latitud de México "
            f"(x {pts[:, 0].min():.2f}…{pts[:, 0].max():.2f}, y {pts[:, 1].min():.2f}…{pts[:, 1].max():.2f}). "
            "El INEGI pudo cambiar el formato del servicio; usa el método con shapefiles (--origen)."
        )


def _prop(properties: dict[str, Any], *names: str) -> str:
    for name in names:
        for key in (name, name.upper()):
            value = properties.get(key)
            if value not in (None, ""):
                return str(value)
    return ""


def _write(path: Path, features: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    collection = {"type": "FeatureCollection", "features": features}
    path.write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


# ------------------------------------------------------------------------------ proceso
def build(
    out_dir: Path | None = None,
    tolerance: float = 0.005,
    municipal_tolerance: float = 0.002,
    fetch: Fetcher | None = None,
    states: list[str] | None = None,
    pause: float = 0.3,
) -> dict[str, Path]:
    if out_dir is None:
        from processing.common.paths import context

        out_dir = context()[0].boundaries
    fetch = fetch or http_fetch
    codes = states or STATE_CODES
    cache = out_dir / "inegi_servicio"

    state_features: list[dict[str, Any]] = []
    national_polygons: list[Any] = []
    municipal_total = 0
    for number, code in enumerate(codes, start=1):
        raw, new_s = cached_fetch(f"{BASE_URL}/mgee/{code}", cache / f"mgee_{code}.json", fetch)
        feature = raw["features"][0]
        props = feature.get("properties") or {}
        name = _prop(props, "nomgeo", "nom_ent") or code
        _check_coordinates(feature["geometry"], name)
        geometry = simplify_geometry(feature["geometry"], tolerance)
        state_features.append(
            {"type": "Feature", "properties": {"code": code, "name": name}, "geometry": geometry}
        )
        national_polygons.extend(
            _polygons_of(simplify_geometry(feature["geometry"], tolerance * 2))
        )

        raw_m, new_m = cached_fetch(f"{BASE_URL}/mgem/{code}", cache / f"mgem_{code}.json", fetch)
        municipal = []
        for f in raw_m["features"]:
            p = f.get("properties") or {}
            mcode = _prop(p, "cvegeo") or code + _prop(p, "cve_mun").zfill(3)
            municipal.append(
                {
                    "type": "Feature",
                    "properties": {
                        "code": mcode[:5],
                        "name": _prop(p, "nomgeo", "nom_mun") or mcode,
                        "state_code": code,
                    },
                    "geometry": simplify_geometry(f["geometry"], municipal_tolerance),
                }
            )
        municipal.sort(key=lambda f: f["properties"]["code"])
        _write(out_dir / "municipalities" / f"{code}.geojson", municipal)
        municipal_total += len(municipal)
        logger.info("[%2d/%d] %s: %d municipios", number, len(codes), name, len(municipal))
        if pause and (new_s or new_m):
            time.sleep(pause)  # pausa de cortesía con el servidor, solo si hubo descarga

    state_features.sort(key=lambda f: f["properties"]["code"])
    _write(out_dir / "states.geojson", state_features)
    _write(
        out_dir / "mexico.geojson",
        [
            {
                "type": "Feature",
                "properties": {
                    "name": "México",
                    "note": "Unión de los polígonos estatales (sin disolver fronteras internas).",
                },
                "geometry": {"type": "MultiPolygon", "coordinates": national_polygons},
            }
        ],
    )
    logger.info(
        "Límites listos en %s: %d estados y %d municipios.",
        out_dir,
        len(state_features),
        municipal_total,
    )
    return {
        "states": out_dir / "states.geojson",
        "municipalities": out_dir / "municipalities",
        "mexico": out_dir / "mexico.geojson",
    }
