"""Temperatura superficial terrestre: MOD11A2 V061 (Terra MODIS, 1 km, 8 días).

Pasos científicos (ver products.json → processing):
1. Filtro de calidad con QC_Day: se acepta calidad obligatoria 00, o 01 con
   error medio de LST ≤ 2 K. Se descartan 10 (nubes), 11 y el relleno 0.
2. LST_Day_1km × 0.02 = K; K − 273.15 = °C.
3. Promedio mensual ponderado por los días de cada compuesto que caen en el
   mes; se exige al menos 50 % de días cubiertos.
4. Desde 2020 se marca la bandera "deriva_orbital_terra": la hora de paso de
   Terra se adelanta y eso tiende a registrar superficies más frías.
"""

from __future__ import annotations

import numpy as np

from app.services.dates import iter_months
from processing.common import modis, qc

VARIABLE = "temperature"


def _convert(raw: np.ndarray, qc_layer: np.ndarray) -> tuple[np.ndarray, None]:
    good = qc.mod11_good(raw, qc_layer)
    return np.where(good, qc.lst_to_celsius(raw), np.nan).astype("float32"), None


def spec() -> modis.ModisSpec:
    return modis.ModisSpec(
        variable=VARIABLE,
        appeears_product="MOD11A2.061",
        value_layer="LST_Day_1km",
        qc_layer="QC_Day",
        how="mean",
        min_coverage=0.5,
        convert=_convert,
    )


def download(start: str, end: str) -> None:
    for year, first, last in modis.year_ranges(start, end):
        modis.download_year(spec(), year, first=first, last=last)


def process(start: str, end: str) -> list:
    return [modis.process_month(spec(), y, m) for y, m in iter_months(start, end)]
