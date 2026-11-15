"""Pruebas de las rutas HTTP con el cliente de pruebas de FastAPI.

Se omiten automáticamente si FastAPI o httpx no están instalados.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from app.api.deps import get_service  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client(demo_service):
    app.dependency_overrides[get_service] = lambda: demo_service
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["mode"] == "demo"


def test_variables(client):
    body = client.get("/api/variables").json()
    assert len(body["variables"]) == 4


def test_layer_and_alias_are_equal(client):
    a = client.get("/api/layers/precipitation", params={"year": 2015, "month": 7}).json()
    b = client.get("/api/precipitation", params={"year": 2015, "month": 7}).json()
    assert a == b and a["mode"] == "demo"


def test_validation_errors(client):
    assert (
        client.get("/api/layers/precipitation", params={"year": 1999, "month": 7}).status_code
        == 422
    )
    assert client.get("/api/layers/lluvia", params={"year": 2015, "month": 7}).status_code == 422
    response = client.get("/api/no2", params={"year": 2003, "month": 1})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "fecha_sin_datos"


def test_timeseries_csv(client):
    response = client.get(
        "/api/export/timeseries.csv",
        params={
            "variable": "temperature",
            "lat": 25,
            "lon": -105,
            "start": "2015-01",
            "end": "2015-03",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "SIMULADOS" in response.text


def test_cors_header(client):
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
