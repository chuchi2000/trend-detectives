"""Prueba punto-en-polígono vectorizada para geometrías GeoJSON.

Se usa para saber qué celdas de la malla común caen dentro de un estado o
municipio (criterio: el centro de la celda está dentro del polígono). Funciona
con Polygon y MultiPolygon, incluidos huecos, sin depender de Shapely.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _ring_contains(ring: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Algoritmo de cruce de rayos (par/impar) para un anillo."""
    inside = np.zeros(x.shape, dtype=bool)
    xs, ys = ring[:, 0], ring[:, 1]
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi, xj, yj = xs[i], ys[i], xs[j], ys[j]
        crosses = (yi > y) != (yj > y)
        if crosses.any():
            with np.errstate(divide="ignore", invalid="ignore"):
                x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
            inside ^= crosses & (x < x_cross)
        j = i
    return inside


def _polygon_contains(rings: list[Any], x: np.ndarray, y: np.ndarray) -> np.ndarray:
    outer = np.asarray(rings[0], dtype=float)
    result = _ring_contains(outer, x, y)
    for hole in rings[1:]:
        result &= ~_ring_contains(np.asarray(hole, dtype=float), x, y)
    return result


def bbox_of(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    coords: list[np.ndarray] = []
    polygons = (
        geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    )
    for polygon in polygons:
        coords.append(np.asarray(polygon[0], dtype=float))
    stacked = np.vstack(coords)
    return (
        float(stacked[:, 0].min()),
        float(stacked[:, 1].min()),
        float(stacked[:, 0].max()),
        float(stacked[:, 1].max()),
    )


def points_in_geometry(geometry: dict[str, Any], x: np.ndarray, y: np.ndarray) -> np.ndarray:
    gtype = geometry["type"]
    if gtype == "Polygon":
        polygons = [geometry["coordinates"]]
    elif gtype == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError(f"Geometría {gtype} no soportada (se esperan polígonos).")

    west, south, east, north = bbox_of(geometry)
    candidates = (x >= west) & (x <= east) & (y >= south) & (y <= north)
    result = np.zeros(x.shape, dtype=bool)
    if not candidates.any():
        return result
    xc, yc = x[candidates], y[candidates]
    hit = np.zeros(xc.shape, dtype=bool)
    for polygon in polygons:
        hit |= _polygon_contains(polygon, xc, yc)
    result[candidates] = hit
    return result
