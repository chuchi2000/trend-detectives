"""Pruebas del análisis de tendencias mensuales (trend_monthly, trend_map y la API)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.services.trend_map import trend_map
from app.services.trend_monthly import analyze_trend, verdict
from app.services.trend_service import monthly_trend, terra_note, trend_period


def _synthetic(n_pixels: int, slope_per_year: float, seed: int = 0) -> tuple[list[str], np.ndarray]:
    """Ciclo anual + tendencia + ruido AR(1) (r ≈ 0.5), como en trend-detectives."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2004-01-01", "2023-12-01", freq="MS")
    years = np.arange(len(dates)) / 12
    cube = np.empty((len(dates), 1, n_pixels))
    for p in range(n_pixels):
        noise = np.zeros(len(dates))
        for i in range(1, len(dates)):
            noise[i] = 0.5 * noise[i - 1] + rng.normal(0, 0.7)
        cube[:, 0, p] = 15 + 5 * np.sin(2 * np.pi * years) + slope_per_year * years + noise
    return [f"{d:%Y-%m}" for d in dates], cube


def test_analyze_trend_recovers_known_slope():
    dates, cube = _synthetic(1, 0.1)
    result = analyze_trend(pd.Series(cube[:, 0, 0], index=pd.to_datetime(dates)), relative=False)
    assert result["ci95"][0] < 1.0 < result["ci95"][1]
    assert result["t_test_p_value"] < 0.05
    assert 0.2 < result["lag1_autocorrelation"] < 0.8
    assert result["effective_months"] < result["months"]
    assert result["pct_change_per_decade"] is None


def test_monthly_trend_never_returns_nan_p_value():
    """pymannkendall da p = NaN en esta serie (varianza negativa); el servicio usa el
    Mann–Kendall con corrección AR(1) de stats.py y lo indica en una nota."""
    dates, cube = _synthetic(1, 0.1)
    values = [float(v) for v in cube[:, 0, 0]]
    raw = analyze_trend(pd.Series(values, index=pd.to_datetime(dates)))
    result = monthly_trend("precipitation", dates, values, 1.0, "mm/mes", "este punto")
    assert result is not None and np.isfinite(result["p_value"])
    assert result["significant"] and result["direction"] == "increasing"
    if not np.isfinite(raw["p_value"]):
        assert any("Hamed–Rao no convergió" in n for n in result["notes"])


def test_trend_map_matches_analyze_trend_pixel_by_pixel():
    dates, cube = _synthetic(6, 0.03, seed=1)
    r = trend_map(cube, dates, relative=False)
    for p in range(cube.shape[2]):
        one = analyze_trend(pd.Series(cube[:, 0, p], index=pd.to_datetime(dates)), relative=False)
        assert r["slope_per_decade"][0, p] == pytest.approx(one["slope_per_decade"], abs=1e-4)
        assert r["t_test_p_value"][0, p] == pytest.approx(one["t_test_p_value"], abs=1e-12)
        assert r["ci95_low"][0, p] == pytest.approx(one["ci95"][0], abs=1e-4)


def test_trend_map_keeps_missing_data_as_nan():
    dates, cube = _synthetic(3, 0.03)
    cube[:, 0, 0] = np.nan  # píxel sin ningún dato (mar)
    cube[:20, 0, 1] = np.nan  # píxel con huecos: sigue calculándose
    cube[:-10, 0, 2] = np.nan  # solo 10 meses: menos de 24, queda sin dato
    r = trend_map(cube, dates)
    assert np.isnan(r["slope_per_decade"][0, 0]) and not r["significant"][0, 0]
    assert np.isfinite(r["slope_per_decade"][0, 1])
    assert np.isnan(r["slope_per_decade"][0, 2])


def test_verdict_thresholds():
    assert verdict(0.01) == "solida"
    assert verdict(0.07) == "indicio"
    assert verdict(0.5) == "variabilidad"


def test_temperature_period_is_cut_before_terra_drift():
    assert trend_period("temperature", "2004-01", "2025-12", explicit_end=False) == (
        "2004-01",
        "2021-12",
        [terra_note()],
    )
    _, end, notes = trend_period("temperature", "2004-01", "2025-12", explicit_end=True)
    assert end == "2025-12" and "Atención" in notes[0]
    assert trend_period("no2", "2004-10", "2025-12", explicit_end=False)[2] == []


# -- API (modo DEMO) -------------------------------------------------------------

pytest.importorskip("httpx")


@pytest.fixture()
def client(demo_service):
    from fastapi.testclient import TestClient

    from app.api.deps import get_service
    from app.main import app

    app.dependency_overrides[get_service] = lambda: demo_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_trend_map_endpoint_returns_grid(client):
    body = client.get("/api/trend-map/no2").json()
    grid = body["grid"]
    n = grid["nx"] * grid["ny"]
    assert len(grid["values"]) == n == len(body["p_value"]) == len(body["significant"])
    assert body["unit"].endswith("por década") and body["relative"] is True
    assert body["summary"]["n_pixels"] > 0


def test_trend_map_temperature_has_no_percent_and_notes(client):
    body = client.get("/api/trend-map/temperature").json()
    assert body["pct_change_per_decade"] is None and body["relative"] is False
    assert body["end"] <= "2021-12" and body["notes"]


def test_trend_map_is_cached(client):
    first = client.get("/api/trend-map/precipitation").json()
    second = client.get("/api/trend-map/precipitation").json()
    assert second["seconds"] == 0.0 and first["grid"] == second["grid"]


def test_timeseries_includes_monthly_trend_and_keeps_old_trend(client):
    body = client.get(
        "/api/timeseries", params={"variable": "no2", "lat": 19.4, "lon": -99.1}
    ).json()
    monthly = body["trend_monthly"]
    assert body["trend"] is not None  # la tendencia anual de Theil–Sen sigue ahí
    assert monthly["verdict"] in {"solida", "indicio", "variabilidad"}
    assert len(monthly["dates"]) == len(monthly["anomalies"]) == len(monthly["trend_line"])
    assert monthly["sentence"]


def test_trend_map_is_clipped_to_mexico_only_for_global_variables(client, demo_service):
    """Precipitación y NO₂ se recortan al país en la vista; temperatura no se toca."""
    outside = ~demo_service.store.national_mask().ravel()
    no2 = client.get("/api/trend-map/no2").json()
    assert all(v is None for v, out in zip(no2["grid"]["values"], outside, strict=True) if out)
    assert not any(s for s, out in zip(no2["significant"], outside, strict=True) if out)
    from app.services.file_store import CLIP_TO_COUNTRY

    assert {"precipitation", "no2"} == CLIP_TO_COUNTRY
