"""Rutas de regiones (estados y municipios del INEGI)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_service
from app.schemas.models import RegionsResponse
from app.services.atlas import AtlasService

router = APIRouter(tags=["Regiones"])
Service = Annotated[AtlasService, Depends(get_service)]
Level = Annotated[Literal["state", "municipality"], Query()]
State = Annotated[
    str | None,
    Query(alias="estado", pattern=r"^\d{2}$", description="Clave de entidad (2 dígitos)"),
]


@router.get("/regions", response_model=RegionsResponse, summary="Lista de estados o municipios")
def regions(service: Service, level: Level = "state", state: State = None) -> RegionsResponse:
    return service.regions_list(level, state)


@router.get("/regions/geojson", summary="Límites simplificados en GeoJSON")
def regions_geojson(
    service: Service, level: Level = "state", state: State = None
) -> dict[str, Any]:
    return service.regions_geojson(level, state)
