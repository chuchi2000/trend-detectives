"""Evapotranspiración: MOD16A2GF V061 (Terra MODIS, 500 m, compuestos de 8 días).

Pasos científicos (ver products.json → processing):
1. ET_500m × 0.1 = mm en el compuesto (kg/m² = mm de agua).
2. Se eliminan el relleno y los códigos especiales 32761–32766 (agua, urbano,
   desierto, nieve, humedal, sin clasificar): NO son ET cero.
3. El producto GF ya rellenó por interpolación las entradas LAI/FPAR de mala
   calidad, así que por defecto NO se descartan píxeles por ET_QC; se guarda
   la fracción con bit 0 = 1 como indicador. `estricto=True` sí los descarta.
4. Total mensual = suma de los días del mes (cada compuesto repartido de forma
   uniforme entre sus días), con al menos 80 % de días cubiertos.
"""

from __future__ import annotations

import numpy as np

from app.services.dates import iter_months
from processing.common import modis, qc

VARIABLE = "evapotranspiration"


def _convert(strict: bool):  # noqa: ANN202
    def convert(raw: np.ndarray, qc_layer: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        valid = qc.mod16_valid(raw)
        other = qc.mod16_other_quality(qc_layer)
        if strict:
            valid &= ~other
        return np.where(valid, qc.et_to_mm(raw), np.nan).astype("float32"), other & valid

    return convert


def spec(strict: bool = False) -> modis.ModisSpec:
    return modis.ModisSpec(
        variable=VARIABLE,
        appeears_product="MOD16A2GF.061",
        value_layer="ET_500m",
        qc_layer="ET_QC_500m",
        how="sum",
        min_coverage=0.8,
        convert=_convert(strict),
    )


def download(start: str, end: str) -> None:
    for year, first, last in modis.year_ranges(start, end):
        modis.download_year(spec(), year, first=first, last=last)


def process(start: str, end: str, strict: bool = False) -> list:
    return [modis.process_month(spec(strict), y, m) for y, m in iter_months(start, end)]
