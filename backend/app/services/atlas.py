"""Lógica de la API, independiente del framework web.

Cada método recibe parámetros simples, valida, consulta la fuente de datos
(DEMO o DATOS REALES) y devuelve un modelo Pydantic. Las rutas de FastAPI en
app/api/routes/ solo llaman a estos métodos.
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.config import Settings
from app.core.errors import InvalidRequest, NotAvailableInMode
from app.schemas.models import (
    Availability,
    CompareResponse,
    CompareSide,
    CorrelationResponse,
    HealthResponse,
    LayerResponse,
    Link,
    MetadataResponse,
    PointResponse,
    RegionItem,
    RegionRef,
    RegionsResponse,
    SeriesPoint,
    StatisticsResponse,
    Stats,
    TimeSeriesResponse,
    Trend,
    VariableInfo,
    VariablesResponse,
)
from app.services import stats as st
from app.services.catalog import Catalog
from app.services.dates import format_ym, parse_ym
from app.services.demo_store import DEMO_NOTE, DemoStore
from app.services.file_store import FileStore
from app.services.grid import CommonGrid
from app.services.products import ProductCatalog
from app.services.regions import MISSING_MESSAGE, RegionService, parse_region
from app.services.store import DataStore

VERSION = "0.1.0"
STATS_METHOD = (
    "Malla común de 0.25°. Promedio y desviación estándar ponderados por área (cos φ); "
    "mediana, mínimo y máximo por celda. Una celda pertenece a la región si su centro cae dentro."
)


@dataclass
class AtlasService:
    settings: Settings
    products: ProductCatalog
    grid: CommonGrid
    store: DataStore
    regions: RegionService

    # -- información general ------------------------------------------------
    @property
    def mode(self) -> str:
        return self.store.mode

    def health(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            mode=self.store.mode,
            version=VERSION,
            boundaries_loaded=self.regions.available,
            titiler_url=self.settings.titiler_url if self.store.mode == "real" else None,
        )

    def _variable_info(self, variable: str) -> VariableInfo:
        p = self.products.get(variable)
        start, end = self.products.availability(variable)
        return VariableInfo(
            id=variable,
            name=p["name"],
            short_label=p["short_label"],
            unit=p["unit"],
            unit_long=p["unit_long"],
            data_type=p["data_type"],
            product=p["product"],
            temporal=p["temporal"],
            spatial=p["spatial"],
            availability=Availability(
                start=start, end=end, processed=self.store.processed_months(variable)
            ),
            processing=p["processing"],
            display=p["display"],
            caveats=p["caveats"],
            sources=[Link(**s) for s in p["sources"]],
        )

    def variables(self) -> VariablesResponse:
        s0, s1 = self.products.study_period
        c0, c1 = self.products.comparison_period
        return VariablesResponse(
            mode=self.store.mode,
            study_period=Availability(start=s0, end=s1),
            comparison_period=Availability(start=c0, end=c1),
            variables=[self._variable_info(v) for v in self.products.variable_ids],
        )

    def metadata(self, variable: str) -> MetadataResponse:
        p = self.products.get(variable)
        return MetadataResponse(
            mode=self.store.mode,
            variable=self._variable_info(variable),
            layers=p["layers"],
            special_values=p.get("special_values"),
            audit_date=self.products.raw["audit_date"],
        )

    # -- validaciones -------------------------------------------------------
    def _check_point(self, lat: float, lon: float) -> None:
        if not (math.isfinite(lat) and math.isfinite(lon)) or not self.grid.contains(lat, lon):
            g = self.grid
            raise InvalidRequest(
                f"La coordenada ({lat}, {lon}) está fuera del área del Atlas "
                f"(lat {g.south}–{g.north}, lon {g.west}–{g.east})."
            )

    def _region(self, region: str | None) -> tuple[RegionRef, np.ndarray]:
        level, code = parse_region(region)
        if level != "national" and not self.regions.available:
            raise InvalidRequest(MISSING_MESSAGE, code="limites_no_cargados")
        national = self.store.national_mask()
        mask = (
            self.regions.mask(level, code, national) & national if level != "national" else national
        )
        return RegionRef(level=level, code=code, name=self.regions.name_of(level, code)), mask

    def _range(self, variable: str, start: str | None, end: str | None) -> tuple[str, str]:
        a0, a1 = self.products.availability(variable)
        try:
            s = format_ym(*parse_ym(start)) if start else a0
            e = format_ym(*parse_ym(end)) if end else a1
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        if s > e:
            raise InvalidRequest("La fecha inicial es posterior a la final.")
        return s, e

    # -- capas --------------------------------------------------------------
    def layer(self, variable: str, year: int, month: int) -> LayerResponse:
        p = self.products.get(variable)
        payload = self.store.map_layer(variable, year, month)
        start, end = self.products.availability(variable)
        product = p["product"]
        return LayerResponse(
            mode=self.store.mode,
            variable=variable,
            date=format_ym(year, month),
            unit=p["unit"],
            display_unit=p["display"]["display_unit"],
            scale=float(p["display"].get("scale", 1)),
            resolution=payload["resolution"],
            source=f"{product['provider']} — {product['short_name']} v{product['version']}",
            data_type=p["data_type"],
            availability=Availability(
                start=start, end=end, processed=self.store.processed_months(variable)
            ),
            quality=payload["quality"],
            layer=payload["layer"],
        )

    def point(self, variable: str, year: int, month: int, lat: float, lon: float) -> PointResponse:
        self._check_point(lat, lon)
        p = self.products.get(variable)
        result = self.store.point_value(variable, year, month, lat, lon)
        scale = float(p["display"].get("scale", 1))
        value = result["value"]
        return PointResponse(
            mode=self.store.mode,
            variable=variable,
            date=format_ym(year, month),
            lat=lat,
            lon=lon,
            value=value,
            unit=p["unit"],
            display_value=None if value is None else value / scale,
            display_unit=p["display"]["display_unit"],
            cell=result["cell"],
            resolution=result["resolution"],
        )

    # -- análisis -----------------------------------------------------------
    def statistics(
        self, variable: str, year: int, month: int, region: str | None
    ) -> StatisticsResponse:
        ref, mask = self._region(region)
        values = self.store.field(variable, year, month)
        p = self.products.get(variable)
        return StatisticsResponse(
            mode=self.store.mode,
            variable=variable,
            date=format_ym(year, month),
            unit=p["unit"],
            region=ref,
            stats=Stats(**st.describe(values, self.grid.area_weights, mask)),
            extremes=st.extreme_locations(values, self.grid.lats, self.grid.lons, mask),
            method=STATS_METHOD,
        )

    def _series(
        self,
        variable: str,
        start: str,
        end: str,
        lat: float | None,
        lon: float | None,
        region: str | None,
    ) -> tuple[dict[str, Any], list[str], list[float | None]]:
        dates, cube = self.store.cube(variable, start, end)
        if lat is not None and lon is not None:
            self._check_point(lat, lon)
            row, col = self.grid.index_of(lat, lon)
            clat, clon = self.grid.cell_center(row, col)
            values = cube[:, row, col] if len(dates) else np.array([])
            target = {
                "type": "point",
                "lat": lat,
                "lon": lon,
                "cell": {"lat": clat, "lon": clon, "res": self.grid.res},
            }
        else:
            ref, mask = self._region(region)
            values = (
                st.regional_mean_series(cube, self.grid.area_weights, mask)
                if len(dates)
                else np.array([])
            )
            target = {"type": "region", **ref.model_dump()}
        return target, dates, [None if not np.isfinite(v) else float(v) for v in values]

    def timeseries(
        self,
        variable: str,
        start: str | None = None,
        end: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        region: str | None = None,
        with_trend: bool = True,
    ) -> TimeSeriesResponse:
        s, e = self._range(variable, start, end)
        p = self.products.get(variable)
        target, dates, values = self._series(variable, s, e, lat, lon, region)
        trend = st.trend(dates, values, p["unit"]) if with_trend else None
        return TimeSeriesResponse(
            mode=self.store.mode,
            variable=variable,
            unit=p["unit"],
            target=target,
            start=dates[0] if dates else s,
            end=dates[-1] if dates else e,
            points=[SeriesPoint(date=d, value=v) for d, v in zip(dates, values, strict=True)],
            trend=Trend(**trend) if trend else None,
            method=(
                "Valor de la celda de 0.25° que contiene el punto."
                if lat is not None
                else "Promedio regional ponderado por área; el mes queda vacío si menos del 50 % del área tiene dato."
            ),
        )

    def correlation(
        self,
        variable_a: str,
        variable_b: str,
        start: str | None = None,
        end: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        region: str | None = None,
    ) -> CorrelationResponse:
        if variable_a == variable_b:
            raise InvalidRequest("Elige dos variables distintas para correlacionar.")
        common = self.products.common_available_range([variable_a, variable_b])
        if common is None:
            raise InvalidRequest("Las dos variables no tienen meses en común.")
        s = max(common[0], format_ym(*parse_ym(start))) if start else common[0]
        e = min(common[1], format_ym(*parse_ym(end))) if end else common[1]
        target, dates_a, values_a = self._series(variable_a, s, e, lat, lon, region)
        _, dates_b, values_b = self._series(variable_b, s, e, lat, lon, region)
        lookup_b = dict(zip(dates_b, values_b, strict=True))
        aligned_b = [lookup_b.get(d) for d in dates_a]
        anomalies_a = st.monthly_anomalies(dates_a, values_a)
        anomalies_b = st.monthly_anomalies(dates_a, aligned_b)
        result = st.pearson(anomalies_a, anomalies_b)
        return CorrelationResponse(
            mode=self.store.mode,
            variables=[variable_a, variable_b],
            target=target,
            start=dates_a[0] if dates_a else None,
            end=dates_a[-1] if dates_a else None,
            method=(
                "Pearson sobre anomalías mensuales (sin ciclo estacional). Valor p e intervalo de "
                "confianza del 95 % con la transformación z de Fisher y el tamaño de muestra "
                "efectivo por autocorrelación (Bretherton et al., 1999)."
            ),
            note="Una correlación no indica que una variable cause la otra.",
            **result,
        )

    def compare(
        self, variable: str, date_a: str, date_b: str, region: str | None
    ) -> CompareResponse:
        try:
            ya, ma = parse_ym(date_a)
            yb, mb = parse_ym(date_b)
        except ValueError as exc:
            raise InvalidRequest(str(exc)) from exc
        ref, mask = self._region(region)
        field_a = self.store.field(variable, ya, ma)
        field_b = self.store.field(variable, yb, mb)
        w = self.grid.area_weights
        stats_a = st.describe(field_a, w, mask)
        stats_b = st.describe(field_b, w, mask)
        both = mask & np.isfinite(field_a) & np.isfinite(field_b)
        diff_mean = pct = frac_up = None
        if both.any():
            diff = (field_b - field_a)[both]
            weights = w[both]
            diff_mean = float(np.sum(weights * diff) / np.sum(weights))
            mean_a = float(np.sum(weights * field_a[both]) / np.sum(weights))
            pct = None if abs(mean_a) < 1e-12 else 100.0 * diff_mean / abs(mean_a)
            frac_up = float((diff > 0).mean())
        return CompareResponse(
            mode=self.store.mode,
            variable=variable,
            unit=self.products.get(variable)["unit"],
            region=ref,
            a=CompareSide(date=format_ym(ya, ma), stats=Stats(**stats_a)),
            b=CompareSide(date=format_ym(yb, mb), stats=Stats(**stats_b)),
            difference_mean=diff_mean,
            percent_change=pct,
            cells_increase_fraction=frac_up,
            method="Diferencia B − A celda por celda en la malla de 0.25°, solo donde ambas fechas tienen dato; promedio ponderado por área.",
        )

    # -- regiones -----------------------------------------------------------
    def regions_list(self, level: str, state: str | None) -> RegionsResponse:
        if level == "state":
            items = self.regions.states()
        elif level == "municipality":
            if not state:
                raise InvalidRequest("Para municipios indica la entidad con el parámetro 'estado'.")
            items = self.regions.municipalities(state)
        else:
            raise InvalidRequest("Nivel inválido: usa 'state' o 'municipality'.")
        return RegionsResponse(
            level=level,  # type: ignore[arg-type]
            available=self.regions.available,
            message=None if self.regions.available else MISSING_MESSAGE,
            items=[RegionItem(**i) for i in items],
        )

    def regions_geojson(self, level: str, state: str | None) -> dict[str, Any]:
        return self.regions.geojson(level, state)

    # -- exportación ----------------------------------------------------------
    def _csv_header(self) -> list[str]:
        lines = [
            f"# Atlas Ambiental de México — modo {'DEMOSTRACIÓN' if self.mode == 'demo' else 'DATOS REALES'}"
        ]
        if self.mode == "demo":
            lines.append(f"# {DEMO_NOTE}")
        return lines

    def timeseries_csv(self, **kwargs: Any) -> str:
        series = self.timeseries(**kwargs, with_trend=True)
        p = self.products.get(series.variable)
        out = io.StringIO()
        for line in self._csv_header():
            out.write(line + "\n")
        out.write(
            f"# Variable: {p['name']} ({p['unit']}) — Producto: {p['product']['short_name']} v{p['product']['version']}\n"
        )
        out.write(f"# Objetivo: {series.target}\n# Método: {series.method}\n")
        t = series.trend
        if t is not None:
            out.write(
                f"# Tendencia: {t.verdict_label}. Pendiente de Sen {t.slope_per_decade:.6g} {t.unit} "
                f"(IC {round(t.confidence * 100)} %: {t.slope_ci_low_per_decade:.6g} a "
                f"{t.slope_ci_high_per_decade:.6g}); Mann–Kendall p = {t.p_value:.4g} "
                f"(sin corregir por autocorrelación: {t.p_value_uncorrected:.4g}); {t.n_years} años.\n"
                f"# Método de tendencia: {t.method}.\n"
            )
        else:
            out.write("# Tendencia: no calculada (se necesitan al menos 8 años completos).\n")
        writer = csv.writer(out)
        writer.writerow(["fecha", f"valor_{p['unit']}"])
        for point in series.points:
            writer.writerow([point.date, "" if point.value is None else f"{point.value:.6g}"])
        return out.getvalue()

    def statistics_csv(self, variable: str, year: int, month: int, region: str | None) -> str:
        result = self.statistics(variable, year, month, region)
        out = io.StringIO()
        for line in self._csv_header():
            out.write(line + "\n")
        out.write(f"# Método: {result.method}\n")
        writer = csv.writer(out)
        writer.writerow(["variable", "fecha", "region", "unidad", *Stats.model_fields.keys()])
        s = result.stats.model_dump()
        writer.writerow(
            [
                variable,
                result.date,
                result.region.name,
                result.unit,
                *[s[k] if s[k] is not None else "" for k in Stats.model_fields],
            ]
        )
        return out.getvalue()

    def raster_file(self, variable: str, year: int, month: int) -> str:
        if not isinstance(self.store, FileStore):
            raise NotAvailableInMode(
                "La descarga de GeoTIFF solo existe en modo DATOS REALES; en DEMO no hay archivos."
            )
        return self.store.raster_path(variable, year, month)


def build_service(settings: Settings) -> AtlasService:
    products = ProductCatalog.from_file(settings.products_file)
    grid_cfg = products.common_grid
    grid = CommonGrid.from_bounds(grid_cfg["bounds"], grid_cfg["resolution_deg"])
    regions = RegionService(settings.boundaries_dir, grid)
    store: DataStore
    if settings.data_mode == "real":
        store = FileStore(settings, products, grid, Catalog(settings.catalog_file), regions)
    else:
        store = DemoStore(products, grid)
    return AtlasService(
        settings=settings, products=products, grid=grid, store=store, regions=regions
    )
