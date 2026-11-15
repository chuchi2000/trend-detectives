"""Filtros de calidad y valores inválidos de cada producto.

Cada función recibe los valores TAL COMO vienen en el archivo (enteros sin
escalar en MODIS) y devuelve una máscara booleana de píxeles válidos. Las
definiciones de bits y códigos están en metadata/sources/products.json, con
sus fuentes oficiales.
"""

from __future__ import annotations

import numpy as np

# --- MOD11A2 (temperatura superficial) --------------------------------------
LST_SCALE = 0.02
LST_FILL = 0
LST_VALID_MIN, LST_VALID_MAX = 7500, 65535

# --- MOD16A2GF (evapotranspiración) -----------------------------------------
ET_SCALE = 0.1
ET_VALID_MIN, ET_VALID_MAX = -32767, 32700
ET_SPECIAL = {
    32767: "relleno",
    32766: "cuerpos de agua",
    32765: "suelo desnudo o vegetación escasa",
    32764: "nieve o hielo perenne",
    32763: "humedales permanentes",
    32762: "zona urbana",
    32761: "sin clasificar",
}
ET_QC_FILL = 255

# --- IMERG y OMNO2d -----------------------------------------------------------
IMERG_FILL = -9999.900390625
OMI_FILL = -1.2676506002282e30


def bits(values: np.ndarray, start: int, count: int) -> np.ndarray:
    """Extrae `count` bits a partir del bit `start` (el bit 0 es el menos significativo)."""
    return (values.astype(np.uint32) >> start) & ((1 << count) - 1)


def mod11_good(lst_raw: np.ndarray, qc: np.ndarray, max_lst_error_code: int = 1) -> np.ndarray:
    """Píxeles aceptados de LST_Day_1km.

    - Valor dentro del rango válido (7500–65535) y distinto del relleno 0.
    - Calidad obligatoria (bits 0-1) = 00, o = 01 con error de LST (bits 6-7)
      ≤ `max_lst_error_code` (1 → error ≤ 2 K).
    """
    in_range = (lst_raw != LST_FILL) & (lst_raw >= LST_VALID_MIN) & (lst_raw <= LST_VALID_MAX)
    mandatory = bits(qc, 0, 2)
    lst_error = bits(qc, 6, 2)
    good_quality = (mandatory == 0) | ((mandatory == 1) & (lst_error <= max_lst_error_code))
    return in_range & good_quality


def lst_to_celsius(lst_raw: np.ndarray) -> np.ndarray:
    return (lst_raw.astype("float32") * LST_SCALE - 273.15).astype("float32")


def mod16_valid(et_raw: np.ndarray) -> np.ndarray:
    """Píxeles con evapotranspiración calculada (excluye relleno y códigos 32761–32767)."""
    special = np.isin(et_raw, list(ET_SPECIAL))
    return (~special) & (et_raw >= ET_VALID_MIN) & (et_raw <= ET_VALID_MAX)


def mod16_other_quality(et_qc: np.ndarray) -> np.ndarray:
    """Bit 0 de ET_QC = 1: algoritmo de respaldo o relleno en la entrada LAI/FPAR."""
    return (et_qc != ET_QC_FILL) & (bits(et_qc, 0, 1) == 1)


def et_to_mm(et_raw: np.ndarray) -> np.ndarray:
    return (et_raw.astype("float32") * ET_SCALE).astype("float32")


def imerg_valid(precip: np.ndarray) -> np.ndarray:
    return np.isfinite(precip) & (precip > IMERG_FILL + 1) & (precip >= 0)


def omi_valid(no2: np.ndarray) -> np.ndarray:
    return np.isfinite(no2) & (no2 > OMI_FILL / 10)


def special_value_counts(et_raw: np.ndarray) -> dict[str, int]:
    """Cuántos píxeles tienen cada código especial (para el informe de calidad)."""
    return {label: int((et_raw == code).sum()) for code, label in ET_SPECIAL.items()}
