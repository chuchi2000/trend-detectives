"""Análisis de tendencia de UNA serie mensual (punto o región).

Copiado del proyecto trend-detectives (src/analysis/trends.py, rama Adri); la
matemática no se modificó. Complementa —no reemplaza— la tendencia de
Theil–Sen sobre promedios anuales de app/services/stats.py.

Pasos: anomalías (se quita el ciclo estacional), pendiente por mínimos
cuadrados, corrección por autocorrelación (n_eff = n·(1 − r₁)/(1 + r₁)) del
error estándar, del IC 95 % y de la prueba t, pendiente de Sen y prueba de
Mann–Kendall con la modificación de Hamed–Rao.

Uso:
    from app.services.trend_monthly import analyze_trend
    result = analyze_trend(series)   # series: pd.Series con índice de fechas mensuales
"""

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy import stats


def remove_seasonality(series: pd.Series) -> pd.Series:
    """Subtracts each month's long-term mean (all Januaries, all Februaries...).

    What remains are the anomalies: whether a month was higher or lower than usual.
    Without this step, the seasonal cycle hides the trend.
    """
    climatology = series.groupby(series.index.month).transform("mean")
    return series - climatology


def effective_sample_size(residuals: np.ndarray) -> tuple[float, float]:
    """Returns (lag-1 autocorrelation, effective sample size) of the residuals.

    Consecutive months are not independent: a warm month tends to follow a warm
    month. So n months carry less information than n independent values would.
    For a first-order autoregressive process: n_eff = n (1 - r1) / (1 + r1).
    """
    n = len(residuals)
    r1 = float(np.corrcoef(residuals[:-1], residuals[1:])[0, 1])
    n_eff = n * (1 - r1) / (1 + r1) if r1 > 0 else n
    return r1, float(min(max(n_eff, 3.0), n))


def analyze_trend(series: pd.Series, alpha: float = 0.05, relative: bool = True) -> dict:
    """Computes the slope, its confidence interval and its significance.

    relative: also give the slope as a % of the mean. Use False for variables
    whose zero is arbitrary, such as temperature in °C.
    """
    series = series.dropna()
    anomalies = remove_seasonality(series)
    n = len(anomalies)
    y = anomalies.values

    # Time in decimal years, so the slope comes out "per year"
    t = np.asarray(series.index.year + (series.index.month - 1) / 12, dtype=float)

    # 1. Linear regression (least squares): slope and its standard error
    reg = stats.linregress(t, y)

    # 2. Correct for autocorrelation: fewer effective months means a larger
    #    standard error and fewer degrees of freedom
    r1, n_eff = effective_sample_size(y - (reg.intercept + reg.slope * t))
    dof = n_eff - 2
    se = reg.stderr * np.sqrt((n - 2) / dof)

    # 3. t-test of the slope and 95 % confidence interval, both corrected
    t_p = 2 * stats.t.sf(abs(reg.slope / se), dof)
    t_crit = stats.t.ppf(1 - alpha / 2, dof)
    ci = (reg.slope - t_crit * se, reg.slope + t_crit * se)

    # 4. Sen's slope: the median of the slopes between every pair of months.
    #    Outliers barely affect it; it is the usual partner of Mann-Kendall.
    sen = stats.theilslopes(y, t).slope

    # 5. Mann-Kendall: is the trend real, or could it be chance?
    # We use the Hamed and Rao modification, which corrects for autocorrelation:
    # in monthly data each month resembles the previous one, and the original
    # test would overstate significance.
    test = mk.hamed_rao_modification_test(y, alpha=alpha)

    slope_decade = float(reg.slope) * 10
    mean = float(series.mean())

    return {
        "slope_per_decade": round(slope_decade, 4),
        "ci95": [round(float(ci[0]) * 10, 4), round(float(ci[1]) * 10, 4)],
        "sen_slope_per_decade": round(float(sen) * 10, 4),
        "pct_change_per_decade": round(100 * slope_decade / mean, 2) if relative and mean else None,
        "p_value": float(test.p),
        "t_test_p_value": float(t_p),
        "significant": bool(test.p < alpha),
        "direction": test.trend,  # "increasing", "decreasing" or "no trend"
        "lag1_autocorrelation": round(r1, 3),
        "effective_months": round(n_eff, 1),
        "mean": round(mean, 4),
        "months": int(n),
        "start": f"{series.index.min():%Y-%m}",
        "end": f"{series.index.max():%Y-%m}",
    }


# -- Agregado para el Atlas: veredicto en lenguaje sencillo -------------------

VERDICTS = {
    "solida": "Tendencia sólida",
    "indicio": "Indicio de tendencia",
    "variabilidad": "Variabilidad natural",
}


def verdict(p_value: float) -> str:
    """p < 0.05 → «solida»; p < 0.10 → «indicio»; si no, «variabilidad»."""
    if p_value < 0.05:
        return "solida"
    if p_value < 0.10:
        return "indicio"
    return "variabilidad"


if __name__ == "__main__":
    # Synthetic test: annual cycle + warming of 0.3 °C per decade + autocorrelated noise
    rng = np.random.default_rng(42)
    dates = pd.date_range("1990-01-01", "2025-12-01", freq="MS")
    years = np.arange(len(dates)) / 12
    noise = np.zeros(len(dates))
    for i in range(1, len(dates)):
        noise[i] = 0.5 * noise[i - 1] + rng.normal(0, 0.7)
    data = 15 + 5 * np.sin(2 * np.pi * years) + 0.03 * years + noise
    series = pd.Series(data, index=dates)

    print("Expected trend: +0.30 per decade, lag-1 autocorrelation about 0.5")
    print(analyze_trend(series, relative=False))
