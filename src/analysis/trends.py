"""Trend analysis for a monthly time series.

Basic usage:
    from trends import analyze_trend
    result = analyze_trend(series)   # series: pd.Series indexed by monthly dates
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


def analyze_trend(series: pd.Series, alpha: float = 0.05) -> dict:
    """Computes the slope, its confidence interval and its significance.

    Returns the fields described in docs/data-format.md.
    """
    series = series.dropna()
    anomalies = remove_seasonality(series)

    # Time in decimal years, so the slope comes out "per year"
    t = series.index.year + (series.index.month - 1) / 12

    # Linear regression: slope and 95 % confidence interval
    reg = stats.linregress(t, anomalies.values)
    t_crit = stats.t.ppf(1 - alpha / 2, df=len(anomalies) - 2)
    ci = (reg.slope - t_crit * reg.stderr, reg.slope + t_crit * reg.stderr)

    # Mann-Kendall: is the trend real, or could it be chance?
    # We use the Hamed and Rao modification, which corrects for autocorrelation:
    # in monthly data each month resembles the previous one, and the original
    # test would overstate significance.
    test = mk.hamed_rao_modification_test(anomalies.values, alpha=alpha)

    slope_decade = float(reg.slope) * 10
    mean = float(series.mean())

    return {
        "slope_per_decade": round(slope_decade, 4),
        "ci95": [round(float(ci[0]) * 10, 4), round(float(ci[1]) * 10, 4)],
        "pct_change_per_decade": round(100 * slope_decade / mean, 2) if mean else None,
        "p_value": float(test.p),
        "significant": bool(test.p < alpha),
        "direction": test.trend,  # "increasing", "decreasing" or "no trend"
        "mean": round(mean, 4),
        "months": int(len(series)),
        "start": f"{series.index.min():%Y-%m}",
        "end": f"{series.index.max():%Y-%m}",
    }


if __name__ == "__main__":
    # Synthetic test: annual cycle + warming of 0.3 °C per decade + noise
    rng = np.random.default_rng(42)
    dates = pd.date_range("1990-01-01", "2025-12-01", freq="MS")
    years = np.arange(len(dates)) / 12
    data = 15 + 5 * np.sin(2 * np.pi * years) + 0.03 * years + rng.normal(0, 0.8, len(dates))
    series = pd.Series(data, index=dates)

    print("Expected trend: +0.30 per decade")
    print(analyze_trend(series))
