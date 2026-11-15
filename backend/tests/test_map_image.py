"""Imagen del mapa generada por la API (sin TiTiler)."""

from __future__ import annotations

import struct
import zlib

import numpy as np
import pytest

from app.services import map_image
from app.services.colormaps import hex_to_rgba

DISPLAY = {
    "scale": 1,
    "breaks": [5, 15, 30, 50, 75, 100, 150, 250],
    "ramp": [
        "#F2F7F2",
        "#D2EBE4",
        "#ADDAD7",
        "#7DC4CB",
        "#53A7BE",
        "#2D89AF",
        "#22699C",
        "#214B81",
        "#202F63",
    ],
}


def decode_png(data: bytes) -> np.ndarray:
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, width, height = 8, b"", 0, 0
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        kind = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length : pos + 12 + length])
        assert crc == zlib.crc32(kind + body)
        if kind == b"IHDR":
            width, height, depth, color = struct.unpack(">IIBB", body[:10])
            assert (depth, color) == (8, 6)
        elif kind == b"IDAT":
            idat += body
        pos += 12 + length
    raw = np.frombuffer(zlib.decompress(idat), dtype="uint8").reshape(height, 1 + width * 4)
    assert (raw[:, 0] == 0).all()
    return raw[:, 1:].reshape(height, width, 4)


def test_colors_match_legend_and_missing_is_transparent():
    values = np.array([[0.0, 5.0, 14.9, 300.0, np.nan]], dtype="float32")
    rgba = map_image.colorize(values, DISPLAY)
    assert rgba[0, 0].tolist() == hex_to_rgba("#F2F7F2")  # < 5 → primera clase
    assert rgba[0, 1].tolist() == hex_to_rgba("#D2EBE4")  # 5 ≤ v < 15
    assert rgba[0, 2].tolist() == hex_to_rgba("#D2EBE4")
    assert rgba[0, 3].tolist() == hex_to_rgba("#202F63")  # ≥ 250 → última clase
    assert rgba[0, 4].tolist() == [0, 0, 0, 0]  # sin dato: transparente, nunca un color


def test_scaled_variable_uses_file_units():
    display = {**DISPLAY, "scale": 1e15, "breaks": [0.5, 1, 1.5, 2, 3, 4, 6, 9]}
    rgba = map_image.colorize(np.array([[2.5e15]]), display)
    assert rgba[0, 0].tolist() == hex_to_rgba(DISPLAY["ramp"][4])  # 2 ≤ 2.5 < 3


def test_mercator_rows_put_each_latitude_in_its_source_row():
    north, res, height = 33.25, 0.025, 760
    rows = map_image.mercator_rows(north, res, height)
    assert len(rows) >= height  # ninguna fila del ráster se pierde
    assert set(rows.tolist()) == set(range(height))
    y_top, y_bottom = map_image.mercator_y(north), map_image.mercator_y(north - res * height)
    centers = y_top - (np.arange(len(rows)) + 0.5) * (y_top - y_bottom) / len(rows)
    lats = map_image.inverse_mercator(centers)
    row_north = north - rows * res
    assert np.all((lats <= row_north + 1e-9) & (lats >= row_north - res - 1e-9))


def test_without_mercator_the_center_would_be_shifted():
    """Justifica la corrección: colocar la imagen lineal en latitud desplazaría el centro."""
    north, south = 33.25, 14.25
    linear_center = (north + south) / 2
    y_mid = (map_image.mercator_y(north) + map_image.mercator_y(south)) / 2
    true_lat_at_middle = float(map_image.inverse_mercator(np.array([y_mid]))[0])
    shift_km = abs(true_lat_at_middle - linear_center) * 111.32
    assert shift_km > 30


def test_render_produces_a_valid_png():
    values = np.full((76, 130), 20.0, dtype="float32")
    values[:10] = np.nan
    image = decode_png(map_image.render(values, 33.25, 0.25, DISPLAY))
    assert image.shape[1] == 130 and image.shape[0] >= 76
    assert image[0, 0, 3] == 0  # norte sin dato → transparente
    assert image[-1, 0].tolist() == hex_to_rgba(DISPLAY["ramp"][2])


def test_image_in_demo_mode_is_refused():
    from app.core.config import Settings
    from app.core.errors import NotAvailableInMode
    from app.services.atlas import build_service

    service = build_service(Settings(data_mode="demo"))
    with pytest.raises(NotAvailableInMode):
        service.layer_image("precipitation", 2015, 7)
