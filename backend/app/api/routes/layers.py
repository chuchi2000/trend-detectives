"""Rutas de capas del mapa y consulta por punto.

`GET /api/layers/{variable}?year=&month=` es la ruta general. También existen
los atajos propuestos en el plan: /api/precipitation, /api/no2,
/api/evapotranspiration y /api/temperature con los mismos parámetros.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import VariableId, get_service
from app.schemas.models import LayerResponse, PointResponse
from app.services.atlas import AtlasService

router = APIRouter(tags=["Capas"])
Service = Annotated[AtlasService, Depends(get_service)]
Year = Annotated[int, Query(ge=2000, le=2025, description="Año (2000–2025)")]
Month = Annotated[int, Query(ge=1, le=12, description="Mes (1–12)")]


@router.get(
    "/layers/{variable}", response_model=LayerResponse, summary="Capa mensual de una variable"
)
def layer(variable: VariableId, year: Year, month: Month, service: Service) -> LayerResponse:
    return service.layer(variable, year, month)


def _alias(variable: str):  # noqa: ANN202 - fábrica de rutas
    def handler(year: Year, month: Month, service: Service) -> LayerResponse:
        return service.layer(variable, year, month)

    handler.__name__ = f"layer_{variable}"
    return handler


for _variable in ("precipitation", "no2", "evapotranspiration", "temperature"):
    router.add_api_route(
        f"/{_variable}",
        _alias(_variable),
        methods=["GET"],
        response_model=LayerResponse,
        summary=f"Atajo: capa mensual de {_variable}",
    )


@router.get(
    "/point", response_model=PointResponse, summary="Valor de una variable en una coordenada"
)
def point(
    variable: VariableId,
    year: Year,
    month: Month,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    service: Service,
) -> PointResponse:
    return service.point(variable, year, month, lat, lon)
