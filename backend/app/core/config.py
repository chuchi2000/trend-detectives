"""Configuración del backend leída de variables de entorno.

Se lee el archivo `.env` de la raíz del proyecto (si existe) y después las
variables del sistema, que tienen prioridad. No se usa ninguna librería extra:
el formato es el clásico CLAVE=valor, una por línea.

Las credenciales de NASA Earthdata NO se usan en la API; solo los scripts de
procesamiento las leen (ver processing/common/earthdata.py).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


class Settings(BaseModel):
    data_mode: Literal["demo", "real"] = "demo"
    data_dir: Path = PROJECT_ROOT / "data"
    metadata_dir: Path = PROJECT_ROOT / "metadata"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    # imagen: la API genera el PNG del mapa (no necesita Docker). titiler: teselas de TiTiler.
    map_mode: Literal["imagen", "titiler"] = "imagen"
    titiler_url: str = "http://localhost:8001"
    # Ruta de la carpeta data/ tal como la ve el contenedor de TiTiler.
    titiler_data_dir: str = "/data"
    log_level: str = "INFO"

    @property
    def products_file(self) -> Path:
        return self.metadata_dir / "sources" / "products.json"

    @property
    def catalog_file(self) -> Path:
        return self.data_dir / "catalog" / "catalog.json"

    @property
    def boundaries_dir(self) -> Path:
        return self.data_dir / "boundaries"


def load_dotenv_into_environ() -> None:
    """Copia las claves del .env al entorno del proceso sin sobrescribir las existentes.

    La usan los scripts de procesamiento para que earthaccess encuentre
    EARTHDATA_USERNAME / EARTHDATA_PASSWORD definidos en el .env.
    """
    for key, value in _read_dotenv(PROJECT_ROOT / ".env").items():
        os.environ.setdefault(key, value)


def load_settings(env: dict[str, str] | None = None) -> Settings:
    merged = _read_dotenv(PROJECT_ROOT / ".env")
    merged.update(os.environ if env is None else env)

    kwargs: dict[str, object] = {}
    if "ATLAS_DATA_MODE" in merged:
        kwargs["data_mode"] = merged["ATLAS_DATA_MODE"].strip().lower()
    if "ATLAS_DATA_DIR" in merged:
        kwargs["data_dir"] = Path(merged["ATLAS_DATA_DIR"]).expanduser()
    if "ATLAS_METADATA_DIR" in merged:
        kwargs["metadata_dir"] = Path(merged["ATLAS_METADATA_DIR"]).expanduser()
    if "ATLAS_CORS_ORIGINS" in merged:
        kwargs["cors_origins"] = [
            o.strip() for o in merged["ATLAS_CORS_ORIGINS"].split(",") if o.strip()
        ]
    if merged.get("ATLAS_MAP_MODE"):
        kwargs["map_mode"] = merged["ATLAS_MAP_MODE"].strip().lower()
    if "TITILER_URL" in merged:
        kwargs["titiler_url"] = merged["TITILER_URL"].rstrip("/")
    if "TITILER_DATA_DIR" in merged:
        kwargs["titiler_data_dir"] = merged["TITILER_DATA_DIR"].rstrip("/")
    if "ATLAS_LOG_LEVEL" in merged:
        kwargs["log_level"] = merged["ATLAS_LOG_LEVEL"].upper()
    return Settings(**kwargs)


@lru_cache
def get_settings() -> Settings:
    return load_settings()
