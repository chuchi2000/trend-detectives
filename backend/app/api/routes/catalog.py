"""Rutas de información: salud, variables y metadatos."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import VariableId, get_service
from app.schemas.models import HealthResponse, MetadataResponse, VariablesResponse
from app.services.atlas import AtlasService

router = APIRouter(tags=["Información"])
Service = Annotated[AtlasService, Depends(get_service)]


@router.get("/health", response_model=HealthResponse, summary="Estado del servicio y modo de datos")
def health(service: Service) -> HealthResponse:
    return service.health()


@router.get(
    "/variables",
    response_model=VariablesResponse,
    summary="Las cuatro variables y su disponibilidad",
)
def variables(service: Service) -> VariablesResponse:
    return service.variables()


@router.get(
    "/metadata/{variable}",
    response_model=MetadataResponse,
    summary="Ficha técnica auditada del producto",
)
def metadata(variable: VariableId, service: Service) -> MetadataResponse:
    return service.metadata(variable)
