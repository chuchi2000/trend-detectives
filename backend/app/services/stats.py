"""Estadística descriptiva, tendencias y correlaciones.

Todos los métodos están documentados en docs/05-procesamiento-nasa.md y son
reproducibles: dados los mismos datos, devuelven exactamente lo mismo.

- Promedio y desviación estándar ponderados por área (cos de la latitud),
  porque las celdas de 0.25° son más pequeñas hacia el norte.
- Mediana, mínimo y máximo sin ponderar (describen valores de celda).
- Tendencia: pendiente de Theil–Sen sobre promedios anuales, prueba de
  Mann–Kendall (corrección por empates y por autocorrelación: Hamed y Rao,
  1998; Yue y Wang, 2004) e intervalo de confianza de la pendiente (Sen, 1968). Veredicto:
  «sólida» si p < α y el intervalo no incluye el cero; si no, «indicio» o
  «variabilidad natural». Detalle en metadata/documentation/metodos-estadisticos.md.
- Correlación: Pearson sobre anomalías mensuales (se quita el ciclo estacional),
  con tamaño de muestra efectivo por autocorrelación (Bretherton et al., 1999),
  valor p e intervalo de confianza por la transformación z de Fisher.
"""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import NormalDist
from typing import Any

import numpy as np


def normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def describe(
    values: np.ndarray, weights: np.ndarray, mask: np.ndarray | None = None
) -> dict[str, Any]:
    """Resumen de un campo 2D. `mask` limita el cálculo a una región."""
    region = np.ones(values.shape, dtype=bool) if mask is None else mask.astype(bool)
    n_cells = int(region.sum())
    valid = region & np.isfinite(values)
    n_valid = int(valid.sum())
    if n_valid == 0:
        return {
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "std": None,
            "n_valid": 0,
            "n_cells": n_cells,
            "coverage": 0.0,
        }
    v = values[valid].astype(float)
    w = weights[valid].astype(float)
    mean = float(np.sum(w * v) / np.sum(w))
    variance = float(np.sum(w * (v - mean) ** 2) / np.sum(w))
    return {
        "mean": mean,
        "median": float(np.median(v)),
        "min": float(v.min()),
        "max": float(v.max()),
        "std": math.sqrt(variance),
        "n_valid": n_valid,
        "n_cells": n_cells,
        "coverage": n_valid / n_cells if n_cells else 0.0,
    }


def extreme_locations(
    values: np.ndarray, lats: np.ndarray, lons: np.ndarray, mask: np.ndarray | None = None
) -> dict[str, Any]:
    region = np.ones(values.shape, dtype=bool) if mask is None else mask.astype(bool)
    data = np.where(region & np.isfinite(values), values, np.nan)
    if np.all(np.isnan(data)):
        return {"min": None, "max": None}
    rmin, cmin = np.unravel_index(np.nanargmin(data), data.shape)
    rmax, cmax = np.unravel_index(np.nanargmax(data), data.shape)
    return {
        "min": {
            "lat": float(lats[rmin]),
            "lon": float(lons[cmin]),
            "value": float(data[rmin, cmin]),
        },
        "max": {
            "lat": float(lats[rmax]),
            "lon": float(lons[cmax]),
            "value": float(data[rmax, cmax]),
        },
    }


def regional_mean_series(
    cube: np.ndarray, weights: np.ndarray, mask: np.ndarray, min_coverage: float = 0.5
) -> np.ndarray:
    """Promedio ponderado por área de cada paso de tiempo dentro de `mask`.

    Si menos de `min_coverage` del área de la región tiene dato, ese mes queda NaN.
    """
    w = np.where(mask, weights, 0.0)
    total = w.sum()
    out = np.full(cube.shape[0], np.nan)
    if total == 0:
        return out
    for t in range(cube.shape[0]):
        field = cube[t]
        valid = np.isfinite(field) & mask
        wv = np.where(valid, weights, 0.0)
        if wv.sum() / total >= min_coverage:
            out[t] = float(np.sum(wv * np.where(valid, field, 0.0)) / wv.sum())
    return out


# -- tendencia ---------------------------------------------------------------


def annual_means(
    dates: list[str], values: list[float | None], min_months: int = 9
) -> tuple[list[int], list[float]]:
    """Promedio anual con al menos `min_months` meses válidos."""
    by_year: dict[int, list[float]] = defaultdict(list)
    for date, value in zip(dates, values, strict=True):
        if value is not None and math.isfinite(value):
            by_year[int(date[:4])].append(value)
    years = sorted(y for y, vals in by_year.items() if len(vals) >= min_months)
    return years, [float(np.mean(by_year[y])) for y in years]


def theil_sen(x: list[float] | np.ndarray, y: list[float] | np.ndarray) -> tuple[float, float]:
    slopes = pairwise_slopes(x, y)
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    slope = float(np.median(slopes))
    intercept = float(np.median(ya - slope * xa))
    return slope, intercept


def pairwise_slopes(x: list[float] | np.ndarray, y: list[float] | np.ndarray) -> np.ndarray:
    """Todas las pendientes entre pares de puntos (base de Theil–Sen), ordenadas."""
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    i, j = np.triu_indices(len(xa), k=1)
    dx = xa[j] - xa[i]
    keep = dx != 0
    return np.sort((ya[j] - ya[i])[keep] / dx[keep])


def _z_quantile(confidence: float) -> float:
    return NormalDist().inv_cdf(1 - (1 - confidence) / 2)


def lag_autocorrelation(values: np.ndarray, lag: int) -> float:
    """Autocorrelación de una serie a un desfase dado (0 si no se puede calcular)."""
    a, b = values[:-lag], values[lag:]
    if len(a) < 3 or a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def mann_kendall(
    y: list[float] | np.ndarray, x: list[float] | np.ndarray | None = None
) -> dict[str, float]:
    """Prueba de Mann–Kendall con corrección por autocorrelación.

    La variabilidad natural (por ejemplo, varios años El Niño o La Niña seguidos)
    produce autocorrelación: años parecidos uno tras otro. Eso hace que la prueba
    clásica encuentre «tendencias» con demasiada facilidad.

    Corrección (tamaño de muestra efectivo de Hamed y Rao, 1998, bajo un proceso
    AR(1), como en Yue y Wang, 2004):

        Var*(S) = Var(S) · [1 + 2/(n(n−1)(n−2)) · Σₖ (n−k)(n−k−1)(n−k−2) ρ₁ᵏ]

    ρ₁ es la autocorrelación de orden 1 de la serie sin tendencia, corregida por
    el sesgo de muestras cortas: ρ₁ = (n·r₁ + 1)/(n − 4). Solo se aplica si ρ₁ > 0,
    de modo que la corrección siempre hace la prueba más exigente, nunca menos.
    """
    ya = np.asarray(y, float)
    n = len(ya)
    s = 0.0
    for i in range(n - 1):
        s += float(np.sign(ya[i + 1 :] - ya[i]).sum())
    _, counts = np.unique(ya, return_counts=True)
    ties = sum(c * (c - 1) * (2 * c + 5) for c in counts if c > 1)
    var_s = (n * (n - 1) * (2 * n + 5) - ties) / 18.0

    xa = np.arange(n, dtype=float) if x is None else np.asarray(x, float)
    correction, rho = 1.0, 0.0
    if n > 4:
        slope, intercept = theil_sen(xa, ya)
        residuals = ya - (slope * xa + intercept)
        r1 = lag_autocorrelation(residuals, 1)
        rho = min(max((n * r1 + 1) / (n - 4), 0.0), 0.95)
        if rho > 0:
            total = sum((n - k) * (n - k - 1) * (n - k - 2) * rho**k for k in range(1, n - 2))
            correction = 1 + 2 * total / (n * (n - 1) * (n - 2))
    var_corrected = var_s * correction

    def z_of(variance: float) -> float:
        if variance <= 0 or s == 0:
            return 0.0
        return (s - math.copysign(1, s)) / math.sqrt(variance)

    z = z_of(var_corrected)
    return {
        "s": s,
        "var_s": var_s,
        "var_s_corrected": var_corrected,
        "correction_factor": correction,
        "lag1_autocorrelation": rho,
        "z": z,
        "p_value": 2 * (1 - normal_cdf(abs(z))),
        "p_value_uncorrected": 2 * (1 - normal_cdf(abs(z_of(var_s)))),
    }


def sen_confidence_interval(
    slopes: np.ndarray, var_s: float, confidence: float = 0.95
) -> tuple[float, float]:
    """Intervalo de confianza de la pendiente de Sen (Sen, 1968; Gilbert, 1987, cap. 16).

    C = z(1-α/2)·√Var(S); los límites son las pendientes ordenadas en las posiciones
    (N - C)/2 y (N + C)/2 + 1, con N el número de pendientes entre pares.
    """
    n_slopes = len(slopes)
    c = _z_quantile(confidence) * math.sqrt(var_s)
    lower_rank = (n_slopes - c) / 2
    upper_rank = (n_slopes + c) / 2 + 1

    def at(rank: float) -> float:
        # Interpolación lineal entre pendientes ordenadas (posiciones desde 1).
        position = min(max(rank, 1.0), float(n_slopes)) - 1
        low = int(math.floor(position))
        high = min(low + 1, n_slopes - 1)
        return float(slopes[low] + (slopes[high] - slopes[low]) * (position - low))

    return at(lower_rank), at(upper_rank)


VERDICTS = {
    "solida": "Tendencia sólida",
    "indicio": "Indicio de tendencia, no concluyente",
    "variabilidad": "No se distingue de la variabilidad natural",
}


def trend(
    dates: list[str],
    values: list[float | None],
    unit: str,
    min_years: int = 8,
    confidence: float = 0.95,
) -> dict[str, Any] | None:
    years, means = annual_means(dates, values)
    if len(years) < min_years:
        return None
    slopes = pairwise_slopes(years, means)
    slope, intercept = theil_sen(years, means)
    mk = mann_kendall(means, years)
    ci_low, ci_high = sen_confidence_interval(slopes, mk["var_s_corrected"], confidence)
    alpha = 1 - confidence
    excludes_zero = ci_low > 0 or ci_high < 0
    if mk["p_value"] < alpha and excludes_zero:
        verdict = "solida"
    elif mk["p_value"] < 2 * alpha:
        verdict = "indicio"
    else:
        verdict = "variabilidad"

    residuals = np.asarray(means) - (slope * np.asarray(years, float) + intercept)
    noise = float(np.std(residuals, ddof=1)) if len(residuals) > 2 else 0.0
    change = slope * (years[-1] - years[0])
    signal_to_noise = abs(change) / noise if noise > 0 else None

    direction = "al alza" if slope > 0 else "a la baja"
    pct = int(round(confidence * 100))
    if verdict == "solida":
        reading = (
            f"Tendencia {direction} sólida: la prueba de Mann–Kendall la detecta (p = "
            f"{mk['p_value']:.3f}) y el intervalo de confianza del {pct} % de la pendiente "
            "no incluye el cero. Es poco probable que sea solo variabilidad natural."
        )
    elif verdict == "indicio":
        reading = (
            f"Hay un indicio de tendencia {direction} (p = {mk['p_value']:.3f}), pero no alcanza "
            f"el nivel de confianza del {pct} %. Con más años de datos podría confirmarse o desaparecer."
        )
    else:
        reading = (
            f"El cambio observado (p = {mk['p_value']:.3f}) es compatible con la variabilidad "
            f"natural de un año a otro: el intervalo del {pct} % de la pendiente incluye el cero."
        )
    if mk["correction_factor"] > 1.0:
        reading += (
            " Los años consecutivos se parecen entre sí (autocorrelación), por lo que la prueba "
            "se corrigió para ser más exigente."
        )
    return {
        "method": (
            "Pendiente de Theil–Sen sobre promedios anuales (años con ≥ 9 meses válidos), prueba "
            "de Mann–Kendall con corrección por autocorrelación (Hamed y Rao, 1998; Yue y Wang, "
            f"2004) e intervalo de confianza del {pct} % de la pendiente (Sen, 1968)"
        ),
        "slope_per_decade": slope * 10,
        "slope_ci_low_per_decade": ci_low * 10,
        "slope_ci_high_per_decade": ci_high * 10,
        "confidence": confidence,
        "unit": f"{unit} por década",
        "intercept": intercept,
        "p_value": mk["p_value"],
        "p_value_uncorrected": mk["p_value_uncorrected"],
        "kendall_s": mk["s"],
        "z": mk["z"],
        "autocorrelation_lag1": mk["lag1_autocorrelation"],
        "autocorrelation_factor": mk["correction_factor"],
        "signal_to_noise": signal_to_noise,
        "n_years": len(years),
        "years": years,
        "annual_means": means,
        "significant": verdict == "solida",
        "verdict": verdict,
        "verdict_label": VERDICTS[verdict],
        "interpretation": reading,
    }


# -- correlación ---------------------------------------------------------------


def monthly_anomalies(dates: list[str], values: list[float | None]) -> list[float | None]:
    """Resta a cada mes el promedio de ese mes del año (quita el ciclo estacional)."""
    by_month: dict[int, list[float]] = defaultdict(list)
    for date, value in zip(dates, values, strict=True):
        if value is not None and math.isfinite(value):
            by_month[int(date[5:7])].append(value)
    climatology = {m: float(np.mean(v)) for m, v in by_month.items()}
    out: list[float | None] = []
    for date, value in zip(dates, values, strict=True):
        if value is None or not math.isfinite(value):
            out.append(None)
        else:
            out.append(value - climatology[int(date[5:7])])
    return out


def paired_lag1(values: list[float | None]) -> float:
    """Autocorrelación a un mes usando solo pares de meses consecutivos con dato."""
    pairs = [
        (a, b)
        for a, b in zip(values[:-1], values[1:], strict=True)
        if a is not None and b is not None and math.isfinite(a) and math.isfinite(b)
    ]
    if len(pairs) < 4:
        return 0.0
    xa = np.array([p[0] for p in pairs])
    ya = np.array([p[1] for p in pairs])
    if xa.std() == 0 or ya.std() == 0:
        return 0.0
    return float(np.corrcoef(xa, ya)[0, 1])


def pearson(
    a: list[float | None], b: list[float | None], confidence: float = 0.95
) -> dict[str, Any]:
    """Pearson con tamaño de muestra efectivo e intervalo de confianza.

    Las anomalías mensuales están autocorrelacionadas (un mes húmedo suele seguir a
    otro), así que hay menos información independiente que meses. Se usa el tamaño
    efectivo de Bretherton et al. (1999): n_ef = n·(1 − r₁ₐ·r₁ᵦ)/(1 + r₁ₐ·r₁ᵦ),
    y con él el valor p y el intervalo de confianza por la transformación z de Fisher.
    """
    empty = {
        "r": None,
        "r2": None,
        "n": 0,
        "n_effective": None,
        "p_value": None,
        "ci_low": None,
        "ci_high": None,
        "confidence": confidence,
    }
    pairs = [
        (x, y)
        for x, y in zip(a, b, strict=True)
        if x is not None and y is not None and math.isfinite(x) and math.isfinite(y)
    ]
    n = len(pairs)
    if n < 4:
        return {**empty, "n": n}
    xa = np.array([p[0] for p in pairs])
    ya = np.array([p[1] for p in pairs])
    if xa.std() == 0 or ya.std() == 0:
        return {**empty, "n": n}
    r = float(np.corrcoef(xa, ya)[0, 1])
    product = paired_lag1(a) * paired_lag1(b)
    n_eff = n * (1 - product) / (1 + product) if product > 0 else float(n)
    n_eff = max(min(n_eff, float(n)), 4.0)
    r_clipped = max(min(r, 0.999999), -0.999999)
    fz = math.atanh(r_clipped)
    se = 1 / math.sqrt(n_eff - 3) if n_eff > 3 else float("inf")
    p = 2 * (1 - normal_cdf(abs(fz) / se))
    q = _z_quantile(confidence)
    return {
        "r": r,
        "r2": r * r,
        "n": n,
        "n_effective": n_eff,
        "p_value": p,
        "ci_low": math.tanh(fz - q * se),
        "ci_high": math.tanh(fz + q * se),
        "confidence": confidence,
    }
