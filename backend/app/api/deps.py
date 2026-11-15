"""Dependencias compartidas por las rutas (inyección de dependencias de FastAPI)."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from app.core.config import get_settings
from app.services.atlas import AtlasService, build_service

VariableId = Literal["precipitation", "no2", "evapotranspiration", "temperature"]


@lru_cache
def get_service() -> AtlasService:
    return build_service(get_settings())
