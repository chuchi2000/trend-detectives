"""Rutas de análisis: estadísticas, series de tiempo, correlación y comparación."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import VariableId, get_service
from app.schemas.models import (
    CompareResponse,
    CorrelationResponse,
    StatisticsResponse,
    TimeSeriesResponse,
)
from app.services.atlas import AtlasService

router = APIRouter(tags=["Análisis"])
Service = Annotated[AtlasService, Depends(get_service)]
Year = Annotated[int, Query(ge=2000, le=2025)]
Month = Annotated[int, Query(ge=1, le=12)]
YM = Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$", description="AAAA-MM")]
Region = Annotated[str | None, Query(description="'nacional', 'estado:24' o 'municipio:24028'")]
Lat = Annotated[float | None, Query(ge=-90, le=90)]
Lon = Annotated[float | None, Query(ge=-180, le=180)]


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    summary="Estadística descriptiva de un mes en una región",
)
def statistics(
    variable: VariableId, year: Year, month: Month, service: Service, region: Region = None
) -> StatisticsResponse:
    return service.statistics(variable, year, month, region)


@router.get(
    "/timeseries",
    response_model=TimeSeriesResponse,
    summary="Serie mensual en un punto o una región",
)
def timeseries(
    variable: VariableId,
    service: Service,
    start: YM = None,
    end: YM = None,
    lat: Lat = None,
    lon: Lon = None,
    region: Region = None,
    trend: bool = True,
) -> TimeSeriesResponse:
    return service.timeseries(variable, start, end, lat, lon, region, with_trend=trend)


@router.get(
    "/correlation", response_model=CorrelationResponse, summary="Correlación entre dos variables"
)
def correlation(
    a: VariableId,
    b: VariableId,
    service: Service,
    start: YM = None,
    end: YM = None,
    lat: Lat = None,
    lon: Lon = None,
    region: Region = None,
) -> CorrelationResponse:
    return service.correlation(a, b, start, end, lat, lon, region)


@router.get("/compare", response_model=CompareResponse, summary="Comparación de dos fechas")
def compare(
    variable: VariableId,
    a: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")],
    b: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")],
    service: Service,
    region: Region = None,
) -> CompareResponse:
    return service.compare(variable, a, b, region)
