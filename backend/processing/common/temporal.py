"""Paso de compuestos de 8 días (MODIS) a valores mensuales.

Los compuestos de MODIS empiezan los días 1, 9, 17, ... de cada año y duran 8
días; el último del año dura 5 o 6 días. Un compuesto puede quedar repartido
entre dos meses (por ejemplo, del 29 de enero al 5 de febrero), así que no se
puede asignar completo a un solo mes.

Método (reproducible y documentado en docs/05-procesamiento-nasa.md):

- Cada compuesto aporta a un mes según cuántos de sus días caen en ese mes.
- "sum" (evapotranspiración, que viene como total del compuesto): se reparte el
  total de forma uniforme entre sus días y se suman los días del mes.
- "mean" (temperatura, que viene como promedio del compuesto): promedio
  ponderado por los días que cada compuesto aporta al mes.
- La cobertura es la fracción de días del mes cubiertos por compuestos con dato
  válido en ese píxel. Si es menor que `min_coverage`, el mes queda sin dato.
- En "sum", si la cobertura es suficiente pero incompleta, el total se escala
  por días del mes ÷ días cubiertos (supone que los días faltantes se parecen a
  los cubiertos). Nunca se tratan los faltantes como cero.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Literal

import numpy as np


def composite_length(start: date, nominal_days: int = 8) -> int:
    """Días que cubre un compuesto que empieza en `start` (recortado al fin de año)."""
    year_end = date(start.year, 12, 31)
    return min(nominal_days, (year_end - start).days + 1)


def overlap_days(start: date, length: int, year: int, month: int) -> int:
    end = start + timedelta(days=length - 1)
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    first = max(start, month_start)
    last = min(end, month_end)
    return max(0, (last - first).days + 1)


def composites_for_month(
    starts: list[date], year: int, month: int, nominal_days: int = 8
) -> list[tuple[int, int, int]]:
    """Índices de compuestos que tocan el mes: (índice, días en el mes, duración)."""
    selected = []
    for i, start in enumerate(starts):
        length = composite_length(start, nominal_days)
        days = overlap_days(start, length, year, month)
        if days > 0:
            selected.append((i, days, length))
    return selected


def monthly_from_composites(
    values: np.ndarray,
    starts: list[date],
    year: int,
    month: int,
    how: Literal["sum", "mean"],
    min_coverage: float,
    nominal_days: int = 8,
) -> tuple[np.ndarray, np.ndarray]:
    """Calcula el valor mensual y su cobertura.

    values: arreglo [n_compuestos, ...] con NaN donde no hay dato válido.
    Devuelve (valor_mensual, cobertura) con la forma espacial de `values[0]`.
    """
    n_days = calendar.monthrange(year, month)[1]
    spatial_shape = values.shape[1:]
    accum = np.zeros(spatial_shape, dtype="float64")
    covered = np.zeros(spatial_shape, dtype="float64")
    for index, days, length in composites_for_month(starts, year, month, nominal_days):
        layer = values[index].astype("float64")
        valid = np.isfinite(layer)
        contribution = np.where(valid, layer, 0.0)
        if how == "sum":
            accum += contribution / length * days
        else:
            accum += contribution * days
        covered += valid * days

    coverage = covered / n_days
    with np.errstate(divide="ignore", invalid="ignore"):
        if how == "sum":
            result = accum * (n_days / covered)
        else:
            result = accum / covered
    result = np.where((coverage >= min_coverage) & (covered > 0), result, np.nan)
    return result.astype("float32"), coverage.astype("float32")


def rate_to_monthly_total(rate_mm_per_hour: np.ndarray, year: int, month: int) -> np.ndarray:
    """IMERG mensual da una tasa media en mm/h; el total del mes es tasa × horas del mes."""
    hours = 24 * calendar.monthrange(year, month)[1]
    return (rate_mm_per_hour * hours).astype("float32")


def doy_to_date(year: int, doy: int) -> date:
    return date(year, 1, 1) + timedelta(days=doy - 1)
