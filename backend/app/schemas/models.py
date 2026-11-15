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


class ImagePayload(BaseModel):
    url: str = Field(description="Ruta del PNG del mapa, relativa a la API (empieza con /api)")
    coordinates: list[list[float]] = Field(
        description="Esquinas [lon, lat]: arriba-izq., arriba-der., abajo-der., abajo-izq."
    )


class LayerRef(BaseModel):
    kind: Literal["grid", "tiles", "image"]
    grid: GridPayload | None = None
    image: ImagePayload | None = None
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


class TrendMonthly(BaseModel):
    """Tendencia sobre anomalías MENSUALES (app/services/trend_monthly.py).

    Complementa a `Trend` (Theil–Sen sobre promedios anuales). Las cantidades
    van en unidades de visualización (`unit`), p. ej. NO₂ en ×10¹⁵ molec/cm².
    """

    method: str
    unit: str = Field(description="Unidad de la pendiente, p. ej. '°C por década'")
    slope_per_decade: float = Field(description="Mínimos cuadrados sobre anomalías")
    ci95: list[float] = Field(description="IC 95 % corregido por autocorrelación")
    sen_slope_per_decade: float
    pct_change_per_decade: float | None = Field(
        description="None para temperatura (cero arbitrario)"
    )
    p_value: float = Field(description="Mann–Kendall con modificación de Hamed–Rao")
    t_test_p_value: float = Field(description="Prueba t con n_eff = n(1−r₁)/(1+r₁)")
    significant: bool
    direction: str
    lag1_autocorrelation: float
    effective_months: float
    mean: float
    months: int
    start: str
    end: str
    verdict: Literal["solida", "indicio", "variabilidad"]
    verdict_label: str
    sentence: str = Field(description="Resumen en lenguaje sencillo")
    notes: list[str] = Field(default_factory=list)
    dates: list[str] = Field(description="Meses usados en el análisis")
    anomalies: list[float | None] = Field(description="Valor menos el promedio de ese mes del año")
    trend_line: list[float] = Field(description="Recta y = ȳ + b·(t − t̄) en cada fecha")


class TimeSeriesResponse(BaseModel):
    mode: DataMode
    variable: str
    unit: str
    target: dict[str, Any]
    start: str
    end: str
    points: list[SeriesPoint]
    trend: Trend | None
    trend_monthly: TrendMonthly | None = None
    method: str


class TrendMapSummary(BaseModel):
    """Resumen sobre las celdas de México con tendencia calculable."""

    n_pixels: int
    fraction_up: float | None
    fraction_significant_up: float | None
    fraction_significant_down: float | None
    median_slope_per_decade: float | None


class TrendMapResponse(BaseModel):
    """Tendencia por píxel de todo el mapa (app/services/trend_map.py).

    Todas las listas siguen el orden de `grid.values`: fila por fila de norte a sur.
    """

    mode: DataMode
    variable: str
    start: str
    end: str
    unit: str = Field(description="Unidad de la pendiente, p. ej. '°C por década'")
    relative: bool = Field(description="Si hay % por década (no en temperatura)")
    grid: GridPayload = Field(description="Pendiente por década en unidades de visualización")
    ci95_low: list[float | None]
    ci95_high: list[float | None]
    p_value: list[float | None] = Field(description="Prueba t corregida por autocorrelación")
    significant: list[bool]
    pct_change_per_decade: list[float | None] | None
    summary: TrendMapSummary
    method: str
    notes: list[str] = Field(default_factory=list)
    seconds: float = Field(description="Tiempo de cálculo (0 si vino de la caché)")


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
