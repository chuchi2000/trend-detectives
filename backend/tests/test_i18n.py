"""Idioma de la API: español por defecto, inglés con ?lang=en o Accept-Language."""

from __future__ import annotations

import pytest

from app.core.i18n import deep_merge, normalize

pytest.importorskip("httpx")


@pytest.fixture()
def client(demo_service):
    from fastapi.testclient import TestClient

    from app.api.deps import get_service
    from app.main import app

    app.dependency_overrides[get_service] = lambda: demo_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_normalize_and_deep_merge():
    assert normalize("en-US") == "en" and normalize("EN") == "en"
    assert normalize(None) == "es" and normalize("fr") == "es"
    base = {"a": 1, "t": "hola", "l": [{"x": 1, "d": "uno"}, {"x": 2, "d": "dos"}], "c": ["a"]}
    over = {"t": "hello", "l": [{"d": "one"}], "c": ["b"], "_comment": "ignored"}
    assert deep_merge(base, over) == {
        "a": 1,
        "t": "hello",
        "l": [{"x": 1, "d": "one"}, {"x": 2, "d": "dos"}],
        "c": ["b"],
    }


def test_variables_are_translated_but_numbers_are_shared(client):
    es = {v["id"]: v for v in client.get("/api/variables").json()["variables"]}
    en = {
        v["id"]: v for v in client.get("/api/variables", params={"lang": "en"}).json()["variables"]
    }
    assert es["precipitation"]["name"] == "Precipitación"
    assert en["precipitation"]["name"] == "Precipitation"
    assert en["precipitation"]["unit"] == "mm/month"
    assert en["precipitation"]["display"]["breaks"] == es["precipitation"]["display"]["breaks"]
    assert en["temperature"]["caveats"][0].startswith("It is the temperature")


def test_error_messages_follow_the_language(client):
    params = {"variable": "no2", "year": 2001, "month": 1}
    es = client.get("/api/layers/no2", params=params).json()["error"]
    en = client.get("/api/layers/no2", params={**params, "lang": "en"}).json()["error"]
    assert es["code"] == en["code"] == "fecha_sin_datos"
    assert "no tiene datos" in es["message"] and "has no data" in en["message"]
    assert "January 2001" in en["message"]


def test_accept_language_header_is_used_without_query(client):
    body = client.get("/api/trend-map/temperature", headers={"Accept-Language": "en-US,en;q=0.9"})
    assert body.json()["unit"] == "°C per decade"


def test_trend_texts_in_english(client):
    trend_map = client.get("/api/trend-map/temperature", params={"lang": "en"}).json()
    assert trend_map["notes"][0].startswith("The temperature trend uses data up to December 2021")
    assert trend_map["method"].startswith("Per 0.25° pixel")
    series = client.get(
        "/api/timeseries", params={"variable": "no2", "lat": 19.4, "lon": -99.1, "lang": "en"}
    ).json()
    monthly = series["trend_monthly"]
    assert monthly["verdict_label"] in {"Solid trend", "Hint of a trend", "Natural variability"}
    assert "this point" in monthly["sentence"] and monthly["unit"].endswith("per decade")
    assert series["trend"]["unit"].endswith("per decade")


def test_trend_map_cache_is_per_language(client):
    es = client.get("/api/trend-map/temperature").json()
    en = client.get("/api/trend-map/temperature", params={"lang": "en"}).json()
    assert es["notes"] != en["notes"] and es["grid"] == en["grid"]


def test_csv_export_in_english(client):
    text = client.get(
        "/api/export/timeseries.csv", params={"variable": "precipitation", "lang": "en"}
    ).text
    assert "# Mexico Environmental Atlas — DEMO mode" in text
    assert "date,value_mm/month" in text
