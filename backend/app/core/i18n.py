"""Idioma de las respuestas de la API (español por defecto, inglés con ?lang=en).

Un middleware (app/main.py) lee `?lang=` (o, si no viene, el encabezado
Accept-Language) y lo guarda en una ContextVar que dura lo que dura la petición.
Los servicios escriben cada texto en los dos idiomas con `tr(es, en)`, así la
lógica no necesita recibir el idioma como parámetro.

Los textos de products.json se traducen con metadata/sources/products.en.json
(ver ProductCatalog), que solo contiene los campos de texto.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any, Literal

Lang = Literal["es", "en"]
SUPPORTED: tuple[Lang, ...] = ("es", "en")

_current: ContextVar[Lang] = ContextVar("atlas_lang", default="es")


def get_lang() -> Lang:
    return _current.get()


def set_lang(value: str | None) -> Token[Lang]:
    return _current.set(normalize(value))


def reset_lang(token: Token[Lang]) -> None:
    _current.reset(token)


def normalize(value: str | None) -> Lang:
    """'en', 'en-US', 'EN' → 'en'; cualquier otra cosa → 'es'."""
    if value and value.strip().lower()[:2] == "en":
        return "en"
    return "es"


def tr(es: str, en: str) -> str:
    """Devuelve el texto en el idioma de la petición actual."""
    return en if _current.get() == "en" else es


def deep_merge(base: Any, overlay: Any) -> Any:
    """Mezcla `overlay` sobre `base`: diccionarios clave por clave, listas de
    diccionarios elemento por elemento; cualquier otro valor se reemplaza."""
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = dict(base)
        for key, value in overlay.items():
            if key.startswith("_"):
                continue
            merged[key] = deep_merge(base[key], value) if key in base else value
        return merged
    if (
        isinstance(base, list)
        and isinstance(overlay, list)
        and all(isinstance(x, dict) for x in base + overlay)
    ):
        return [deep_merge(b, overlay[i]) if i < len(overlay) else b for i, b in enumerate(base)]
    return overlay


# Notas de calidad que escribe el procesamiento en data/catalog/catalog.json.
# Las que no estén aquí se muestran tal cual (en español).
CATALOG_NOTES_EN = {
    "Agregación conservativa ponderada por área a 0.25°.": (
        "Area-weighted conservative aggregation to 0.25°."
    ),
    "Promedio de días válidos; mínimo 3 días por celda.": (
        "Mean of valid days; at least 3 days per cell."
    ),
    "Mapa agregado de la resolución nativa (~0.0042°) a 0.025° por promedio de área.": (
        "Map aggregated from the native resolution (~0.0042°) to 0.025° by area mean."
    ),
    "Mapa agregado de la resolución nativa (~0.0083°) a 0.025° por promedio de área.": (
        "Map aggregated from the native resolution (~0.0083°) to 0.025° by area mean."
    ),
}


def catalog_note(note: str) -> str:
    if get_lang() != "en":
        return note
    if note in CATALOG_NOTES_EN:
        return CATALOG_NOTES_EN[note]
    prefix = "Calculado en Google Earth Engine a partir de "
    if note.startswith(prefix):
        return "Computed in Google Earth Engine from " + note[len(prefix) :]
    return note
