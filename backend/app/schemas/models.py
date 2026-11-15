"""Esquemas de respuesta de la API (Pydantic).

Estos modelos documentan la forma exacta de cada respuesta. FastAPI los usa
para validar y para generar la documentación interactiva en /docs. El frontend
tiene los tipos equivalentes en frontend/src/services/types.ts.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DataMode = Literal["demo", "real"]


class Link(BaseModel):
    label: str
    url: str


class Availability(BaseModel):
    start: str = Field(description="Primer mes con datos válidos (AAAA-MM)")
    end: str = Field(description="Último mes con datos válidos (AAAA-MM)")
    processed: list[str] | None = Field(
        default=None, description="Meses ya procesados (solo en modo DATOS REALES)"
    )


class VariableInfo(BaseModel):
    id: str
    name: str
    short_label: str
    unit: str
    unit_long: str
    data_type: str
    product: dict[str, Any]
    temporal: dict[str, Any]
    spatial: dict[str, Any]
    availability: Availability
    processing: dict[str, Any]
    display: dict[str, Any]
    caveats: list[str]
    sources: list[Link]


class VariablesResponse(BaseModel):
    mode: DataMode
    study_period: Availability
    comparison_period: Availability
    variables: list[VariableInfo]


class MetadataResponse(BaseModel):
    mode: DataMode
    variable: VariableInfo
    layers: list[dict[str, Any]]
    special_values: dict[str, str] | None = None
    audit_date: str


class Quality(BaseModel):
    coverage: float | None = None
    n_valid: int | None = None
    flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class GridPayload(BaseModel):
    west: float
    south: float
    east: float
    north: float
    res: float
    nx: int
    ny: int
    values: list[float | None] = Field(
        description="Fila por fila de norte a sur, en unidades de visualización"
    )


class LayerRef(BaseModel):
    kind: Literal["grid", "tiles"]
    grid: GridPayload | None = None
    tiles: list[str] | None = None
    tile_size: int | None = None
    bounds: list[float] | None = None
    attribution: str


class LayerResponse(BaseModel):
    mode: DataMode
    variable: str
    date: str
    unit: str
    display_unit: str
    scale: float
    resolution: str
    source: str
    data_type: str
    availability: Availability
    quality: Quality
    layer: LayerRef


class Cell(BaseModel):
    lat: float
    lon: float
    res: float


class PointResponse(BaseModel):
    mode: DataMode
    variable: str
    date: str
    lat: float
    lon: float
    value: float | None
    unit: str
    display_value: float | None
    display_unit: str
    cell: Cell | None
    resolution: str


class RegionRef(BaseModel):
    level: Literal["national", "state", "municipality"]
    code: str | None
    name: str


class Stats(BaseModel):
    mean: float | None
    median: float | None
    min: float | None
    max: float | None
    std: float | None
    n_valid: int
    n_cells: int
    coverage: float


class StatisticsResponse(BaseModel):
    mode: DataMode
    variable: str
    date: str
    unit: str
    region: RegionRef
    stats: Stats
    extremes: dict[str, Any]
    method: str


class SeriesPoint(BaseModel):
    date: str
    value: float | None


class Trend(BaseModel):
    method: str
    slope_per_decade: float
    slope_ci_low_per_decade: float
    slope_ci_high_per_decade: float
    confidence: float
    unit: str
    intercept: float
    p_value: float
    p_value_uncorrected: float
    kendall_s: float
    z: float
    autocorrelation_lag1: float
    autocorrelation_factor: float
    signal_to_noise: float | None
    n_years: int
    years: list[int]
    annual_means: list[float]
    significant: bool
    verdict: Literal["solida", "indicio", "variabilidad"]
    verdict_label: str
    interpretation: str


class TimeSeriesResponse(BaseModel):
    mode: DataMode
    variable: str
    unit: str
    target: dict[str, Any]
    start: str
    end: str
    points: list[SeriesPoint]
    trend: Trend | None
    method: str


class CorrelationResponse(BaseModel):
    mode: DataMode
    variables: list[str]
    target: dict[str, Any]
    start: str | None
    end: str | None
    n: int
    n_effective: float | None
    r: float | None
    r2: float | None
    p_value: float | None
    ci_low: float | None
    ci_high: float | None
    confidence: float
    method: str
    note: str


class CompareSide(BaseModel):
    date: str
    stats: Stats


class CompareResponse(BaseModel):
    mode: DataMode
    variable: str
    unit: str
    region: RegionRef
    a: CompareSide
    b: CompareSide
    difference_mean: float | None
    percent_change: float | None
    cells_increase_fraction: float | None
    method: str


class RegionItem(BaseModel):
    level: Literal["state", "municipality"]
    code: str
    name: str
    state_code: str | None = None


class RegionsResponse(BaseModel):
    level: Literal["state", "municipality"]
    available: bool
    message: str | None = None
    items: list[RegionItem]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    mode: DataMode
    version: str
    boundaries_loaded: bool
    titiler_url: str | None
