"""Rutas de exportación: CSV de series y estadísticas, y GeoTIFF del mes."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, PlainTextResponse

from app.api.deps import VariableId, get_service
from app.services.atlas import AtlasService

router = APIRouter(prefix="/export", tags=["Exportación"])
Service = Annotated[AtlasService, Depends(get_service)]
Year = Annotated[int, Query(ge=2000, le=2025)]
Month = Annotated[int, Query(ge=1, le=12)]
YM = Annotated[str | None, Query(pattern=r"^\d{4}-\d{2}$")]


def _csv(content: str, filename: str) -> PlainTextResponse:
    return PlainTextResponse(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/timeseries.csv", summary="Serie de tiempo en CSV")
def timeseries_csv(
    variable: VariableId,
    service: Service,
    start: YM = None,
    end: YM = None,
    lat: Annotated[float | None, Query(ge=-90, le=90)] = None,
    lon: Annotated[float | None, Query(ge=-180, le=180)] = None,
    region: str | None = None,
) -> PlainTextResponse:
    content = service.timeseries_csv(
        variable=variable, start=start, end=end, lat=lat, lon=lon, region=region
    )
    return _csv(content, f"atlas_{service.mode}_{variable}_serie.csv")


@router.get("/statistics.csv", summary="Estadísticas del mes en CSV")
def statistics_csv(
    variable: VariableId, year: Year, month: Month, service: Service, region: str | None = None
) -> PlainTextResponse:
    content = service.statistics_csv(variable, year, month, region)
    return _csv(content, f"atlas_{service.mode}_{variable}_{year}-{month:02d}_estadisticas.csv")


@router.get("/raster", summary="GeoTIFF (COG) mensual en resolución nativa")
def raster(variable: VariableId, year: Year, month: Month, service: Service) -> FileResponse:
    path = Path(service.raster_file(variable, year, month))
    return FileResponse(
        path, media_type="image/tiff", filename=f"atlas_{variable}_{year}-{month:02d}.tif"
    )
