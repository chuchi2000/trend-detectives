"""Pruebas de los métodos para separar tendencias de la variabilidad natural."""

from __future__ import annotations

import numpy as np

from app.services import stats


def _monthly(years: range, annual: list[float]) -> tuple[list[str], list[float | None]]:
    dates, values = [], []
    for year, value in zip(years, annual, strict=True):
        for month in range(1, 13):
            dates.append(f"{year}-{month:02d}")
            values.append(value)
    return dates, values


def test_sen_interval_of_exact_line_is_the_slope():
    slopes = stats.pairwise_slopes(range(10), [2 * x + 1 for x in range(10)])
    low, high = stats.sen_confidence_interval(slopes, var_s=125.0)
    assert low == high == 2.0


def test_clear_trend_is_solid_and_interval_contains_true_slope():
    rng = np.random.default_rng(1)
    years = range(2005, 2025)
    annual = [0.3 * (y - 2005) + rng.normal(0, 0.5) for y in years]
    result = stats.trend(*_monthly(years, annual), unit="°C")
    assert result is not None
    assert result["verdict"] == "solida"
    assert result["slope_ci_low_per_decade"] < 3.0 < result["slope_ci_high_per_decade"]
    assert result["slope_ci_low_per_decade"] > 0


def test_pure_noise_is_mostly_natural_variability():
    """Con ruido sin tendencia, el veredicto 'sólida' debe salir pocas veces (~5 %)."""
    rng = np.random.default_rng(7)
    years = range(2005, 2025)
    solid = 0
    trials = 300
    for _ in range(trials):
        annual = list(rng.normal(20, 1, len(years)))
        if stats.trend(*_monthly(years, annual), unit="°C")["verdict"] == "solida":
            solid += 1
    assert solid / trials < 0.09


def test_autocorrelated_noise_is_corrected():
    """Ruido con 'memoria' (años parecidos seguidos) engaña a la prueba clásica;
    la corrección por autocorrelación reduce esos falsos positivos a la mitad o menos."""
    rng = np.random.default_rng(3)
    corrected, classic = 0, 0
    trials = 300
    for _ in range(trials):
        x = np.zeros(25)
        for t in range(1, 25):
            x[t] = 0.7 * x[t - 1] + rng.normal()
        mk = stats.mann_kendall(x)
        corrected += mk["p_value"] < 0.05
        classic += mk["p_value_uncorrected"] < 0.05
        assert mk["var_s_corrected"] >= mk["var_s"]
    assert corrected < classic / 2


def test_few_years_gives_no_trend():
    assert stats.trend(*_monthly(range(2018, 2024), [1, 2, 3, 4, 5, 6]), unit="mm") is None


def test_correlation_interval_and_effective_sample_size():
    rng = np.random.default_rng(5)
    a = np.zeros(240)
    for t in range(1, 240):
        a[t] = 0.6 * a[t - 1] + rng.normal()
    b = a + rng.normal(0, 1, 240)
    b_ar = np.zeros(240)
    for t in range(1, 240):
        b_ar[t] = 0.6 * b_ar[t - 1] + rng.normal()
    result = stats.pearson(list(a), list(b + 0.0 * b_ar))
    assert result["ci_low"] < result["r"] < result["ci_high"]
    assert result["n_effective"] < result["n"] == 240
    assert result["p_value"] < 0.001
    independent = stats.pearson(list(a), list(b_ar))
    assert independent["ci_low"] < 0 < independent["ci_high"] or independent["p_value"] >= 0.01
