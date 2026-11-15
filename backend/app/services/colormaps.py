"""Escalas de color de la identidad visual, en el formato que entiende TiTiler.

TiTiler acepta un mapa de color por intervalos: una lista de pares
[[mínimo, máximo], [R, G, B, A]]. Así el mapa en el navegador usa exactamente
las mismas 9 clases que la leyenda.
"""

from __future__ import annotations

import json
from typing import Any

LOW_SENTINEL = -1.0e12
HIGH_SENTINEL = 1.0e12


def hex_to_rgba(color: str, alpha: int = 255) -> list[int]:
    color = color.lstrip("#")
    return [int(color[i : i + 2], 16) for i in (0, 2, 4)] + [alpha]


def interval_colormap(display: dict[str, Any]) -> list[list[list[float] | list[int]]]:
    """Construye los intervalos en las unidades del archivo (sin escala de visualización)."""
    scale = float(display.get("scale", 1))
    breaks = [b * scale for b in display["breaks"]]
    edges = [LOW_SENTINEL, *breaks, HIGH_SENTINEL]
    ramp = display["ramp"]
    return [[[edges[i], edges[i + 1]], hex_to_rgba(ramp[i])] for i in range(len(ramp))]


def interval_colormap_param(display: dict[str, Any]) -> str:
    return json.dumps(interval_colormap(display), separators=(",", ":"))
