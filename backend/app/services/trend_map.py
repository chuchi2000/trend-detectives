"""Tendencia de TODOS los píxeles de un cubo mensual a la vez (vectorizado con NumPy).

Copiado del proyecto trend-detectives (rama Adri); la matemática no se modificó.
Mismo método que app.services.trend_monthly.analyze_trend, aplicado a todo el
mapa en menos de un segundo en lugar de recorrer píxel por píxel:
  1. Se quita el ciclo estacional por píxel (cada mes menos el promedio de largo
     plazo de ese mes del calendario) → anomalías.
  2. Pendiente por mínimos cuadrados de las anomalías contra el tiempo (años decimales).
  3. Autocorrelación lag 1 de los residuos → tamaño de muestra efectivo
     n_eff = n (1 − r1) / (1 + r1), que ensancha el error estándar.
  4. Prueba t corregida de la pendiente e intervalo de confianza del 95 %.

Mann–Kendall NO se calcula aquí (es demasiado lento para cada píxel); se calcula
con analyze_trend sobre la serie del punto o la región que se elige.

Uso:
    from app.services.trend_map import trend_map
    result = trend_map(cube, dates)        # cube: (tiempo, lat, lon), dates: ["2004-01", ...]
    result["slope_per_decade"]             # arreglo 2D (lat, lon), NaN donde no se puede calcular
"""

from __future__ import annotations

import numpy as np
from scipy import special


def trend_map(
    cube: np.ndarray,
    dates: list[str],
    alpha: float = 0.05,
    min_months: int = 24,
    relative: bool = True,
) -> dict[str, np.ndarray]:
    """Per-pixel trend of a (time, lat, lon) cube of monthly values.

    cube: float array, NaN = no data (never zero). dates: "YYYY-MM", one per time step.
    relative: also return the slope as % of the mean (use False for °C).
    Returns 2-D arrays (lat, lon): slope_per_decade, ci95_low, ci95_high,
    pct_change_per_decade, t_test_p_value, significant, lag1_autocorrelation,
    effective_months, months, mean.
    """
    data = np.asarray(cube, dtype=float)
    if data.ndim != 3 or data.shape[0] != len(dates):
        raise ValueError("cube must be (time, lat, lon) with one date per time step")
    years = np.array([int(d[:4]) for d in dates])
    months = np.array([int(d[5:7]) for d in dates])
    t = (years + (months - 1) / 12.0)[:, None, None]

    valid = np.isfinite(data)
    n = valid.sum(axis=0).astype(float)

    # 1. Anomalies: subtract each calendar month's mean (per pixel)
    anomalies = np.full_like(data, np.nan)
    for m in range(1, 13):
        sel = months == m
        if not sel.any():
            continue
        block = data[sel]
        with np.errstate(invalid="ignore"), _quiet_nanmean():
            clim = (
                np.nanmean(np.where(np.isfinite(block), block, np.nan), axis=0)
                if np.isfinite(block).any()
                else None
            )
        if clim is not None:
            anomalies[sel] = block - clim
    y = np.where(valid, anomalies, 0.0)
    w = valid.astype(float)

    # 2. Least squares with masks (only valid months count)
    with np.errstate(invalid="ignore", divide="ignore"):
        t_mean = (w * t).sum(axis=0) / n
        y_mean = y.sum(axis=0) / n
        dt = np.where(valid, t - t_mean, 0.0)
        sxx = (dt**2).sum(axis=0)
        slope = (dt * (y - y_mean) * w).sum(axis=0) / sxx
        intercept = y_mean - slope * t_mean
        resid = np.where(valid, y - (intercept + slope * t), np.nan)
        sse = np.nansum(resid**2, axis=0)
        stderr = np.sqrt(sse / (n - 2) / sxx)

        # 3. Lag-1 autocorrelation of residuals (pairs of consecutive valid months)
        a, b = resid[:-1], resid[1:]
        pair = np.isfinite(a) & np.isfinite(b)
        npair = pair.sum(axis=0)
        a0 = np.where(pair, a, 0.0)
        b0 = np.where(pair, b, 0.0)
        am = a0.sum(axis=0) / npair
        bm = b0.sum(axis=0) / npair
        da = np.where(pair, a - am, 0.0)
        db = np.where(pair, b - bm, 0.0)
        r1 = (da * db).sum(axis=0) / np.sqrt((da**2).sum(axis=0) * (db**2).sum(axis=0))
        n_eff = np.where(r1 > 0, n * (1 - r1) / (1 + r1), n)
        n_eff = np.clip(n_eff, 3.0, n)

        # 4. Corrected t-test and confidence interval
        dof = n_eff - 2
        se = stderr * np.sqrt((n - 2) / dof)
        t_stat = slope / se
        p = 2 * special.stdtr(dof, -np.abs(t_stat))
        t_crit = special.stdtrit(dof, 1 - alpha / 2)

        mean = np.where(n > 0, np.nansum(np.where(valid, data, 0.0), axis=0) / n, np.nan)
        pct = 100 * slope * 10 / mean if relative else np.full_like(slope, np.nan)

    ok = (n >= min_months) & (sxx > 0) & np.isfinite(slope)
    nan = np.nan

    def clean(arr: np.ndarray) -> np.ndarray:
        return np.where(ok, arr, nan)

    return {
        "slope_per_decade": clean(slope * 10),
        "ci95_low": clean((slope - t_crit * se) * 10),
        "ci95_high": clean((slope + t_crit * se) * 10),
        "pct_change_per_decade": clean(pct),
        "t_test_p_value": clean(p),
        "significant": np.where(ok, p < alpha, False),
        "lag1_autocorrelation": clean(r1),
        "effective_months": clean(n_eff),
        "months": np.where(ok, n, 0).astype(int),
        "mean": clean(mean),
    }


class _quiet_nanmean:  # noqa: N801 - gestor de contexto pequeño
    """Silencia el aviso «Mean of empty slice» (píxeles de mar sin ningún dato)."""

    def __enter__(self) -> None:
        import warnings

        self._ctx = warnings.catch_warnings()
        self._ctx.__enter__()
        warnings.simplefilter("ignore", RuntimeWarning)

    def __exit__(self, *exc: object) -> None:
        self._ctx.__exit__(*exc)
