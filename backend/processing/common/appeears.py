"""Cliente mínimo de la API de NASA AppEEARS (productos MODIS con sus capas de calidad).

Flujo según la documentación oficial (https://appeears.earthdatacloud.nasa.gov/api/):

1. POST /login con usuario y contraseña de Earthdata (autenticación básica)
   -> token Bearer válido unas 48 horas.
2. POST /task con una solicitud de área (task_type = "area").
3. GET /status/{task_id} hasta que el estado sea "done".
4. GET /bundle/{task_id} para listar archivos y GET /bundle/{task_id}/{file_id}
   para descargarlos (redirige a S3; hay que seguir la redirección).
"""

from __future__ import annotations

import logging
import time
from datetime import date
from pathlib import Path
from typing import Any

from processing.common.earthdata import basic_credentials

API = "https://appeears.earthdatacloud.nasa.gov/api"
logger = logging.getLogger("atlas.appeears")


def bbox_feature_collection(bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    west, south, east, north = bbox
    ring = [[west, south], [east, south], [east, north], [west, north], [west, south]]
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        ],
    }


def area_task(
    name: str,
    product: str,
    layers: list[str],
    start: date,
    end: date,
    bbox: tuple[float, float, float, float],
) -> dict[str, Any]:
    return {
        "task_type": "area",
        "task_name": name,
        "params": {
            "dates": [
                {"startDate": start.strftime("%m-%d-%Y"), "endDate": end.strftime("%m-%d-%Y")}
            ],
            "layers": [{"product": product, "layer": layer} for layer in layers],
            "geo": bbox_feature_collection(bbox),
            "output": {"format": {"type": "geotiff"}, "projection": "geographic"},
        },
    }


class AppEEARSClient:
    def __init__(self) -> None:
        import requests

        self._requests = requests
        self.session = requests.Session()
        self.token: str | None = None

    def login(self) -> None:
        user, password = basic_credentials()
        response = self.session.post(f"{API}/login", auth=(user, password), timeout=60)
        response.raise_for_status()
        self.token = response.json()["token"]
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        logger.info("Sesión iniciada en AppEEARS.")

    def logout(self) -> None:
        if self.token:
            self.session.post(f"{API}/logout", timeout=30)
            self.token = None

    def submit(self, task: dict[str, Any]) -> str:
        response = self.session.post(f"{API}/task", json=task, timeout=120)
        if response.status_code >= 400:
            raise RuntimeError(
                f"AppEEARS rechazó la solicitud ({response.status_code}): {response.text[:500]}"
            )
        task_id = response.json()["task_id"]
        logger.info("Solicitud enviada a AppEEARS: %s (%s)", task["task_name"], task_id)
        return task_id

    def wait(self, task_id: str, poll_seconds: int = 60, timeout_hours: float = 12) -> None:
        deadline = time.monotonic() + timeout_hours * 3600
        while time.monotonic() < deadline:
            response = self.session.get(f"{API}/task/{task_id}", timeout=60)
            if response.status_code == 403:
                self.login()
                continue
            response.raise_for_status()
            status = response.json().get("status")
            logger.info("AppEEARS %s: %s", task_id, status)
            if status == "done":
                return
            if status == "error":
                raise RuntimeError(f"La solicitud {task_id} terminó con error en AppEEARS.")
            time.sleep(poll_seconds)
        raise TimeoutError(f"La solicitud {task_id} no terminó en {timeout_hours} h.")

    def download_bundle(
        self, task_id: str, destination: Path, suffixes: tuple[str, ...] = (".tif",)
    ) -> list[Path]:
        destination.mkdir(parents=True, exist_ok=True)
        files = self.session.get(f"{API}/bundle/{task_id}", timeout=60).json()["files"]
        saved: list[Path] = []
        for item in files:
            name = Path(item["file_name"]).name
            if not name.endswith(suffixes) and not name.endswith((".json", ".csv", ".txt")):
                continue
            target = destination / name
            if target.exists() and target.stat().st_size == item.get("file_size", -1):
                saved.append(target)
                continue
            with self.session.get(
                f"{API}/bundle/{task_id}/{item['file_id']}",
                stream=True,
                allow_redirects=True,
                timeout=600,
            ) as response:
                response.raise_for_status()
                with open(target, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=1 << 20):
                        fh.write(chunk)
            saved.append(target)
        logger.info("Descargados %d archivos en %s", len(saved), destination)
        return saved
