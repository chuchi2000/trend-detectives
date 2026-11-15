"""Lógica de la API, independiente del framework web.

Cada método recibe parámetros simples, valida, consulta la fuente de datos
(DEMO o DATOS REALES) y devuelve un modelo Pydantic. Las rutas de FastAPI en
app/api/routes/ solo llaman a estos métodos.
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.core.config import Settings
from app.core.errors import InvalidRequest, NotAvailableInMode
from app.core.i18n import get_lang, tr
from app.schemas.models import (
    Availability,
    CompareResponse,
    CompareSide,
    CorrelationResponse,
    GridPayload,
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
    TrendMapResponse,
    TrendMonthly,
    VariableInfo,
    VariablesResponse,
)
from app.services import stats as st
from app.services import trend_service as ts
from app.services.catalog import Catalog
from app.services.dates import format_ym, parse_ym
from app.services.demo_store import DemoStore, demo_note
from app.services.file_store import CLIP_TO_COUNTRY, FileStore
from app.services.grid import CommonGrid
from app.services.products import ProductCatalog
from app.services.regions import RegionService, missing_message, parse_region
from app.services.store import DataStore

VERSION = "0.1.0"


def stats_method() -> str:
    return tr(
        "Malla común de 0.25°. Promedio y desviación estándar ponderados por área (cos φ); "
        "mediana, mínimo y máximo por celda. Una celda pertenece a la región si su centro cae dentro.",
        "Common 0.25° grid. Area-weighted (cos φ) mean and standard deviation; median, minimum "
        "and maximum per cell. A cell belongs to the region if its center falls inside it.",
    )


@dataclass
class AtlasService:
    settings: Settings
    products: ProductCatalog
    grid: CommonGrid
    store: DataStore
    regions: RegionService
    # Caché de mapas de tendencia: los cubos no cambian entre peticiones.
    _trend_cache: dict[tuple[str, ...], TrendMapResponse] = field(
        default_factory=dict, repr=False, compare=False
    )

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
                tr(
                    f"La coordenada ({lat}, {lon}) está fuera del área del Atlas "
                    f"(lat {g.south}–{g.north}, lon {g.west}–{g.east}).",
                    f"The coordinate ({lat}, {lon}) is outside the Atlas area "
                    f"(lat {g.south}–{g.north}, lon {g.west}–{g.east}).",
                )
            )

    def _region(self, region: str | None) -> tuple[RegionRef, np.ndarray]:
        level, code = parse_region(region)
        if level != "national" and not self.regions.available:
            raise InvalidRequest(missing_message(), code="limites_no_cargados")
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
            raise InvalidRequest(
                tr(
                    "La fecha inicial es posterior a la final.",
                    "The start date is after the end date.",
                )
            )
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

    def layer_image(self, variable: str, year: int, month: int) -> bytes:
        """PNG del mapa mensual (modo REAL con ATLAS_MAP_MODE=imagen)."""
        render = getattr(self.store, "map_image", None)
        if render is None:
            raise NotAvailableInMode(
                tr(
                    "La imagen del mapa solo existe en modo DATOS REALES; en DEMO el mapa se "
                    "dibuja con la rejilla simulada.",
                    "The map image only exists in REAL DATA mode; in DEMO the map is drawn "
                    "from the simulated grid.",
                )
            )
        return render(variable, year, month)

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
            method=stats_method(),
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
        monthly = None
        if with_trend and dates:
            place = (
                tr("este punto", "this point")
                if target["type"] == "point"
                else target.get("name", tr("la región", "the region"))
            )
            monthly = ts.monthly_trend(
                variable,
                dates,
                values,
                float(p["display"].get("scale", 1)),
                p["display"]["display_unit"],
                place,
            )
        return TimeSeriesResponse(
            mode=self.store.mode,
            variable=variable,
            unit=p["unit"],
            target=target,
            start=dates[0] if dates else s,
            end=dates[-1] if dates else e,
            points=[SeriesPoint(date=d, value=v) for d, v in zip(dates, values, strict=True)],
            trend=Trend(**trend) if trend else None,
            trend_monthly=TrendMonthly(**monthly) if monthly else None,
            method=(
                tr(
                    "Valor de la celda de 0.25° que contiene el punto.",
                    "Value of the 0.25° cell that contains the point.",
                )
                if lat is not None
                else tr(
                    "Promedio regional ponderado por área; el mes queda vacío si menos del 50 % "
                    "del área tiene dato.",
                    "Area-weighted regional mean; the month is left empty if less than 50 % of "
                    "the area has data.",
                )
            ),
        )

    def trend_map(
        self, variable: str, start: str | None = None, end: str | None = None
    ) -> TrendMapResponse:
        """Tendencia por década de cada píxel de 0.25° (prueba t corregida)."""
        s, e = self._range(variable, start, end)
        s, e, notes = ts.trend_period(variable, s, e, explicit_end=end is not None)
        key = (self.store.mode, variable, s, e, get_lang())
        cached = self._trend_cache.get(key)
        if cached is not None:
            return cached.model_copy(update={"seconds": 0.0})

        p = self.products.get(variable)
        dates, cube = self.store.cube(variable, s, e)
        if len(dates) < 24:
            raise InvalidRequest(
                tr(
                    "Se necesitan al menos 24 meses para calcular una tendencia; "
                    f"el periodo {s} a {e} tiene {len(dates)}.",
                    "At least 24 months are needed to compute a trend; "
                    f"the period {s} to {e} has {len(dates)}.",
                )
            )
        scale = float(p["display"].get("scale", 1))
        national = self.store.national_mask()
        r = ts.compute_trend_map(dates, cube, variable, scale, national)
        if variable in CLIP_TO_COUNTRY and national is not None and not national.all():
            # Solo la vista: fuera de México la celda queda «sin dato» (transparente).
            outside = ~national.ravel()
            for name in ("slope", "ci95_low", "ci95_high", "p_value", "pct"):
                if r[name] is not None:
                    r[name] = [None if out else v for v, out in zip(r[name], outside, strict=True)]
            r["significant"] = [
                s and not out for s, out in zip(r["significant"], outside, strict=True)
            ]
        g = self.grid
        unit = f"{p['display']['display_unit']} {tr('por década', 'per decade')}"
        result = TrendMapResponse(
            mode=self.store.mode,
            variable=variable,
            start=dates[0],
            end=dates[-1],
            unit=unit,
            relative=ts.relative_for(variable),
            grid=GridPayload(
                west=g.west,
                south=g.south,
                east=g.east,
                north=g.north,
                res=g.res,
                nx=g.shape[1],
                ny=g.shape[0],
                values=r["slope"],
            ),
            ci95_low=r["ci95_low"],
            ci95_high=r["ci95_high"],
            p_value=r["p_value"],
            significant=r["significant"],
            pct_change_per_decade=r["pct"],
            summary=r["summary"],
            method=ts.map_method(),
            notes=notes,
            seconds=r["seconds"],
        )
        if len(self._trend_cache) >= 32:
            self._trend_cache.pop(next(iter(self._trend_cache)))
        self._trend_cache[key] = result
        return result

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
            raise InvalidRequest(
                tr(
                    "Elige dos variables distintas para correlacionar.",
                    "Choose two different variables to correlate.",
                )
            )
        common = self.products.common_available_range([variable_a, variable_b])
        if common is None:
            raise InvalidRequest(
                tr(
                    "Las dos variables no tienen meses en común.",
                    "The two variables share no months.",
                )
            )
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
                tr(
                    "Pearson sobre anomalías mensuales (sin ciclo estacional). Valor p e intervalo "
                    "de confianza del 95 % con la transformación z de Fisher y el tamaño de muestra "
                    "efectivo por autocorrelación (Bretherton et al., 1999).",
                    "Pearson on monthly anomalies (seasonal cycle removed). p-value and 95 % "
                    "confidence interval with Fisher's z transformation and the effective sample "
                    "size for autocorrelation (Bretherton et al., 1999).",
                )
            ),
            note=tr(
                "Una correlación no indica que una variable cause la otra.",
                "A correlation does not mean that one variable causes the other.",
            ),
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
            method=tr(
                "Diferencia B − A celda por celda en la malla de 0.25°, solo donde ambas fechas "
                "tienen dato; promedio ponderado por área.",
                "Difference B − A cell by cell on the 0.25° grid, only where both dates have "
                "data; area-weighted mean.",
            ),
        )

    # -- regiones -----------------------------------------------------------
    def regions_list(self, level: str, state: str | None) -> RegionsResponse:
        if level == "state":
            items = self.regions.states()
        elif level == "municipality":
            if not state:
                raise InvalidRequest(
                    tr(
                        "Para municipios indica la entidad con el parámetro 'estado'.",
                        "For municipalities, give the state with the 'estado' parameter.",
                    )
                )
            items = self.regions.municipalities(state)
        else:
            raise InvalidRequest(
                tr(
                    "Nivel inválido: usa 'state' o 'municipality'.",
                    "Invalid level: use 'state' or 'municipality'.",
                )
            )
        return RegionsResponse(
            level=level,  # type: ignore[arg-type]
            available=self.regions.available,
            message=None if self.regions.available else missing_message(),
            items=[RegionItem(**i) for i in items],
        )

    def regions_geojson(self, level: str, state: str | None) -> dict[str, Any]:
        return self.regions.geojson(level, state)

    # -- exportación ----------------------------------------------------------
    def _csv_header(self) -> list[str]:
        if self.mode == "demo":
            mode = tr("DEMOSTRACIÓN", "DEMO")
        else:
            mode = tr("DATOS REALES", "REAL DATA")
        lines = [
            tr(
                f"# Atlas Ambiental de México — modo {mode}",
                f"# Mexico Environmental Atlas — {mode} mode",
            )
        ]
        if self.mode == "demo":
            lines.append(f"# {demo_note()}")
        return lines

    def timeseries_csv(self, **kwargs: Any) -> str:
        series = self.timeseries(**kwargs, with_trend=True)
        p = self.products.get(series.variable)
        out = io.StringIO()
        for line in self._csv_header():
            out.write(line + "\n")
        product = f"{p['product']['short_name']} v{p['product']['version']}"
        out.write(
            tr(
                f"# Variable: {p['name']} ({p['unit']}) — Producto: {product}\n",
                f"# Variable: {p['name']} ({p['unit']}) — Product: {product}\n",
            )
        )
        out.write(
            tr(
                f"# Objetivo: {series.target}\n# Método: {series.method}\n",
                f"# Target: {series.target}\n# Method: {series.method}\n",
            )
        )
        t = series.trend
        if t is not None:
            ci = (
                f"{round(t.confidence * 100)} %: {t.slope_ci_low_per_decade:.6g} "
                f"{tr('a', 'to')} {t.slope_ci_high_per_decade:.6g}"
            )
            out.write(
                tr(
                    f"# Tendencia: {t.verdict_label}. Pendiente de Sen {t.slope_per_decade:.6g} "
                    f"{t.unit} (IC {ci}); Mann–Kendall p = {t.p_value:.4g} (sin corregir por "
                    f"autocorrelación: {t.p_value_uncorrected:.4g}); {t.n_years} años.\n"
                    f"# Método de tendencia: {t.method}.\n",
                    f"# Trend: {t.verdict_label}. Sen's slope {t.slope_per_decade:.6g} {t.unit} "
                    f"(CI {ci}); Mann–Kendall p = {t.p_value:.4g} (not corrected for "
                    f"autocorrelation: {t.p_value_uncorrected:.4g}); {t.n_years} years.\n"
                    f"# Trend method: {t.method}.\n",
                )
            )
        else:
            out.write(
                tr(
                    "# Tendencia: no calculada (se necesitan al menos 8 años completos).\n",
                    "# Trend: not computed (at least 8 complete years are needed).\n",
                )
            )
        writer = csv.writer(out)
        writer.writerow([tr("fecha", "date"), f"{tr('valor', 'value')}_{p['unit']}"])
        for point in series.points:
            writer.writerow([point.date, "" if point.value is None else f"{point.value:.6g}"])
        return out.getvalue()

    def statistics_csv(self, variable: str, year: int, month: int, region: str | None) -> str:
        result = self.statistics(variable, year, month, region)
        out = io.StringIO()
        for line in self._csv_header():
            out.write(line + "\n")
        out.write(tr(f"# Método: {result.method}\n", f"# Method: {result.method}\n"))
        writer = csv.writer(out)
        writer.writerow(
            [
                "variable",
                tr("fecha", "date"),
                "region",
                tr("unidad", "unit"),
                *Stats.model_fields.keys(),
            ]
        )
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
                tr(
                    "La descarga de GeoTIFF solo existe en modo DATOS REALES; en DEMO no hay "
                    "archivos.",
                    "GeoTIFF download only exists in REAL DATA mode; DEMO has no files.",
                )
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
