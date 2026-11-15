"""Reglas del Atlas alrededor del análisis de tendencias mensuales.

Las matemáticas viven en trend_monthly.py (una serie) y trend_map.py (todo el
mapa), copiadas tal cual de trend-detectives. Aquí solo se adapta al Atlas:

- Periodo por defecto: la disponibilidad de la variable, salvo temperatura,
  que se corta en 2021-12 (ver terra_note()).
- Unidades de visualización: la serie se divide entre `display.scale` antes del
  análisis (NO₂ queda en ×10¹⁵ molec/cm²), igual que el mapa del mes.
- Frase en lenguaje sencillo y veredicto (p < 0.05 sólida; p < 0.10 indicio),
  en español o inglés según el idioma de la petición (app/core/i18n.py).
"""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np
import pandas as pd

from app.core.i18n import get_lang, tr
from app.services import stats as st
from app.services.dates import parse_ym
from app.services.trend_map import trend_map
from app.services.trend_monthly import analyze_trend, remove_seasonality, verdict

# La temperatura viene de MODIS Terra (LST de día). Terra dejó de corregir su
# órbita en 2020 y su hora de paso se adelantó: el suelo se mide más temprano
# (más frío) y 2022–2025 sale de 2 a 4 °C por debajo de lo normal. Con esos
# años, el mapa de tendencia «enfría» México de forma artificial.
TREND_DEFAULT_END = {"temperature": "2021-12"}


def terra_note() -> str:
    return tr(
        "La tendencia de temperatura usa hasta diciembre de 2021: desde 2022 la deriva de la "
        "órbita del satélite Terra adelanta la hora de medición y enfría artificialmente los datos.",
        "The temperature trend uses data up to December 2021: since 2022 the orbital drift of the "
        "Terra satellite makes it measure earlier in the day, which artificially cools the data.",
    )


def terra_warning() -> str:
    return tr(
        "Atención: este periodo incluye 2022 o después, cuando la deriva de la órbita de Terra "
        "enfría artificialmente la temperatura de superficie. La tendencia puede salir a la baja "
        "sin que el enfriamiento sea real.",
        "Warning: this period includes 2022 or later, when Terra's orbital drift artificially "
        "cools the surface temperature. The trend may come out downward without any real cooling.",
    )


def map_method() -> str:
    return tr(
        "Por píxel de 0.25°: se quita el ciclo estacional (cada mes menos el promedio de ese mes "
        "del año), pendiente por mínimos cuadrados de las anomalías y prueba t con el tamaño de "
        "muestra efectivo n_eff = n(1 − r₁)/(1 + r₁) por la autocorrelación de los residuos. "
        "Píxeles con menos de 24 meses válidos quedan sin dato.",
        "Per 0.25° pixel: the seasonal cycle is removed (each month minus the mean of that "
        "calendar month), least-squares slope of the anomalies and t-test with the effective "
        "sample size n_eff = n(1 − r₁)/(1 + r₁) for the autocorrelation of the residuals. "
        "Pixels with fewer than 24 valid months have no data.",
    )


def series_method() -> str:
    return tr(
        "Anomalías mensuales (sin ciclo estacional); pendiente por mínimos cuadrados con IC 95 % "
        "y prueba t corregidos por autocorrelación (n_eff = n(1 − r₁)/(1 + r₁)); pendiente de "
        "Sen; prueba de Mann–Kendall con la modificación de Hamed y Rao (valor p principal).",
        "Monthly anomalies (seasonal cycle removed); least-squares slope with 95 % CI and t-test "
        "corrected for autocorrelation (n_eff = n(1 − r₁)/(1 + r₁)); Sen's slope; Mann–Kendall "
        "test with the Hamed and Rao modification (main p-value).",
    )


VERDICT_LABELS = {
    "solida": ("Tendencia sólida", "Solid trend"),
    "indicio": ("Indicio de tendencia", "Hint of a trend"),
    "variabilidad": ("Variabilidad natural", "Natural variability"),
}

SUBJECT = {
    "precipitation": ("la precipitación", "precipitation"),
    "no2": ("el NO₂ troposférico", "tropospheric NO₂"),
    "evapotranspiration": ("la evapotranspiración", "evapotranspiration"),
    "temperature": ("la temperatura de la superficie", "the land surface temperature"),
}


def relative_for(variable: str) -> bool:
    """El % por década no tiene sentido con °C (el cero es arbitrario)."""
    return variable != "temperature"


def trend_period(
    variable: str, start: str, end: str, explicit_end: bool
) -> tuple[str, str, list[str]]:
    """Ajusta el fin del periodo (temperatura) y devuelve las notas que lo explican."""
    cut = TREND_DEFAULT_END.get(variable)
    if cut is None:
        return start, end, []
    if not explicit_end and end > cut:
        return start, cut, [terra_note()]
    if end > cut:
        return start, end, [terra_warning()]
    return start, end, []


def _round(value: float, digits: int = 5) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return float(f"{value:.{digits}g}")


def _to_list(array: np.ndarray, digits: int = 5) -> list[float | None]:
    return [_round(float(v), digits) for v in np.asarray(array, dtype=float).ravel()]


def compute_trend_map(
    dates: list[str], cube: np.ndarray, variable: str, scale: float, mask: np.ndarray
) -> dict[str, Any]:
    """Corre trend_map sobre el cubo (en unidades de visualización) y arma la respuesta."""
    started = time.perf_counter()
    r = trend_map(np.asarray(cube, dtype=float) / scale, dates, relative=relative_for(variable))
    seconds = time.perf_counter() - started

    slope = r["slope_per_decade"]
    inside = mask & np.isfinite(slope)
    n = int(inside.sum())
    sig = r["significant"] & inside
    summary = {
        "n_pixels": n,
        "fraction_up": float((slope[inside] > 0).mean()) if n else None,
        "fraction_significant_up": float((sig & (slope > 0)).sum() / n) if n else None,
        "fraction_significant_down": float((sig & (slope < 0)).sum() / n) if n else None,
        "median_slope_per_decade": _round(float(np.median(slope[inside]))) if n else None,
    }
    return {
        "slope": _to_list(slope),
        "ci95_low": _to_list(r["ci95_low"]),
        "ci95_high": _to_list(r["ci95_high"]),
        "p_value": _to_list(r["t_test_p_value"], 4),
        "significant": [bool(v) for v in r["significant"].ravel()],
        "pct": _to_list(r["pct_change_per_decade"], 4) if relative_for(variable) else None,
        "summary": summary,
        "seconds": round(seconds, 3),
    }


def _sentence(
    variable: str, result: dict[str, Any], display_unit: str, place: str, kind: str
) -> str:
    slope = result["slope_per_decade"]
    year0, year1 = result["start"][:4], result["end"][:4]
    amount = f"{abs(slope):.2f} {display_unit}"
    pct = result["pct_change_per_decade"]
    if get_lang() == "en":
        subject = SUBJECT.get(variable, ("", "the variable"))[1]
        pct_text = f" ({abs(pct):.1f} % per decade)" if pct is not None else ""
        if kind == "variabilidad":
            return (
                f"Between {year0} and {year1}, {subject} at {place} changed "
                f"{'+' if slope >= 0 else '−'}{amount} per decade{pct_text}, but the change "
                "cannot be told apart from natural month-to-month variability."
            )
        verb = "risen" if slope > 0 else "fallen"
        text = f"Since {year0}, {subject} at {place} has {verb} {amount} per decade{pct_text}"
        if kind == "indicio":
            return text + "; this is a hint, not yet conclusive."
        return text + "."
    subject = SUBJECT.get(variable, ("la variable", ""))[0]
    pct_text = f" ({abs(pct):.1f} % por década)" if pct is not None else ""
    if kind == "variabilidad":
        return (
            f"Entre {year0} y {year1}, {subject} en {place} cambió {'+' if slope >= 0 else '−'}"
            f"{amount} por década{pct_text}, pero el cambio no se distingue de la variabilidad "
            "natural de un mes a otro."
        )
    verb = "subido" if slope > 0 else "bajado"
    text = f"Desde {year0}, {subject} en {place} ha {verb} {amount} por década{pct_text}"
    if kind == "indicio":
        return text + "; es un indicio, todavía no concluyente."
    return text + "."


def monthly_trend(
    variable: str,
    dates: list[str],
    values: list[float | None],
    scale: float,
    display_unit: str,
    place: str,
) -> dict[str, Any] | None:
    """analyze_trend sobre la serie del punto o región, con veredicto y gráfica."""
    _, end, notes = trend_period(
        variable, dates[0] if dates else "", dates[-1] if dates else "", False
    )
    keep = [i for i, d in enumerate(dates) if d <= end]
    if not keep:
        return None
    use_dates = [dates[i] for i in keep]
    raw = [values[i] for i in keep]
    series = pd.Series(
        [np.nan if v is None else v / scale for v in raw],
        index=pd.to_datetime(use_dates),
        dtype=float,
    )
    valid = series.dropna()
    if len(valid) < 24 or valid.nunique() < 3:
        return None

    result = analyze_trend(series, relative=relative_for(variable))
    anomalies = remove_seasonality(valid).reindex(series.index)
    if not math.isfinite(result["p_value"]):
        # pymannkendall (Hamed–Rao completo) a veces estima una varianza negativa con
        # series largas de tendencia fuerte y devuelve p = NaN. Se usa entonces el
        # Mann–Kendall del Atlas (stats.py: corrección AR(1) de Hamed–Rao / Yue–Wang),
        # que nunca reduce la varianza.
        fallback = st.mann_kendall(
            valid.values - valid.groupby(valid.index.month).transform("mean").values
        )
        p = float(fallback["p_value"])
        result["p_value"] = p
        result["significant"] = p < 0.05
        if p < 0.05:
            result["direction"] = "increasing" if fallback["s"] > 0 else "decreasing"
        else:
            result["direction"] = "no trend"
        notes = [
            *notes,
            tr(
                "La versión completa de Hamed–Rao no convergió para esta serie; el valor p de "
                "Mann–Kendall usa la corrección AR(1) de Hamed y Rao (Yue y Wang, 2004).",
                "The full Hamed–Rao version did not converge for this series; the Mann–Kendall "
                "p-value uses the AR(1) correction of Hamed and Rao (Yue and Wang, 2004).",
            ),
        ]
    kind = verdict(result["p_value"])
    unit = f"{display_unit} {tr('por década', 'per decade')}"

    t = np.array([y + (m - 1) / 12 for y, m in (parse_ym(d) for d in use_dates)], dtype=float)
    t_valid = t[np.isfinite(series.values)]
    slope_year = result["slope_per_decade"] / 10
    y_mean = float(np.nanmean(anomalies.values))
    line = y_mean + slope_year * (t - float(t_valid.mean()))

    return {
        **result,
        "method": series_method(),
        "unit": unit,
        "verdict": kind,
        "verdict_label": tr(*VERDICT_LABELS[kind]),
        "sentence": _sentence(variable, result, display_unit, place, kind),
        "notes": notes,
        "dates": use_dates,
        "anomalies": [None if not np.isfinite(v) else _round(float(v)) for v in anomalies.values],
        "trend_line": [float(_round(float(v)) or 0.0) for v in line],
    }
