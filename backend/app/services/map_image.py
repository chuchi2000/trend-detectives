"""Imagen PNG del mapa mensual, generada por la propia API (sin TiTiler ni Docker).

El ráster mensual está en una malla de grados (EPSG:4326). El mapa web usa la
proyección Web Mercator, donde las filas de latitud no están igualmente espaciadas.
Si se coloca la imagen tal cual entre sus cuatro esquinas, el centro de México queda
desplazado decenas de kilómetros. Por eso las filas se reordenan a espaciado Mercator
(vecino más cercano, sin inventar valores) antes de colorear. Las columnas no cambian:
en Mercator la longitud ya es lineal.

Solo depende de NumPy y de la biblioteca estándar (zlib, struct) para escribir el PNG.
"""

from __future__ import annotations

import math
import struct
import zlib
from typing import Any

import numpy as np

from app.services.colormaps import hex_to_rgba


def mercator_y(lat_deg: np.ndarray | float) -> np.ndarray | float:
    lat = np.radians(lat_deg)
    return np.log(np.tan(np.pi / 4 + lat / 2))


def inverse_mercator(y: np.ndarray) -> np.ndarray:
    return np.degrees(2 * np.arctan(np.exp(y)) - np.pi / 2)


def mercator_rows(north: float, res_y: float, height: int) -> np.ndarray:
    """Para cada fila de la imagen en Mercator, la fila del ráster que le corresponde.

    La imagen tiene suficientes filas para que ninguna fila del ráster se pierda (la
    fila más delgada en Mercator es la más cercana al ecuador)."""
    south = north - res_y * height
    y_top, y_bottom = float(mercator_y(north)), float(mercator_y(south))
    thinnest = float(mercator_y(south + res_y)) - y_bottom
    out_height = max(height, math.ceil(round((y_top - y_bottom) / thinnest, 6)))
    centers = y_top - (np.arange(out_height) + 0.5) * (y_top - y_bottom) / out_height
    lats = inverse_mercator(centers)
    rows = np.floor((north - lats) / res_y).astype(int)
    return np.clip(rows, 0, height - 1)


def colorize(values: np.ndarray, display: dict[str, Any]) -> np.ndarray:
    """RGBA (uint8) con las 9 clases de la leyenda. Sin dato → transparente."""
    scale = float(display.get("scale", 1))
    breaks = np.asarray(display["breaks"], dtype="float64") * scale
    ramp = np.asarray([hex_to_rgba(c) for c in display["ramp"]], dtype="uint8")
    finite = np.isfinite(values)
    classes = np.searchsorted(breaks, np.where(finite, values, 0.0), side="right")
    rgba = ramp[np.clip(classes, 0, len(ramp) - 1)]
    rgba[~finite] = 0
    return rgba


def encode_png(rgba: np.ndarray) -> bytes:
    """PNG RGBA de 8 bits (sin dependencias)."""
    height, width, _ = rgba.shape
    raw = np.empty((height, 1 + width * 4), dtype="uint8")
    raw[:, 0] = 0  # filtro "None" en cada fila
    raw[:, 1:] = rgba.reshape(height, width * 4)

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw.tobytes(), 6))
        + chunk(b"IEND", b"")
    )


def render(values: np.ndarray, north: float, res_y: float, display: dict[str, Any]) -> bytes:
    """Ráster (norte arriba, filas de res_y grados) → PNG listo para el mapa web."""
    rows = mercator_rows(north, res_y, values.shape[0])
    return encode_png(colorize(values[rows], display))


def corners(west: float, south: float, east: float, north: float) -> list[list[float]]:
    """Esquinas en el orden que pide MapLibre: arriba-izq., arriba-der., abajo-der., abajo-izq."""
    return [[west, north], [east, north], [east, south], [west, south]]
