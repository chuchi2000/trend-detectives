"""Pruebas de los servicios de la API en modo DEMO."""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.core.config import PROJECT_ROOT
from app.core.errors import DateUnavailable, InvalidRequest, NotAvailableInMode
from app.services import stats
from app.services.colormaps import interval_colormap
from app.services.products import ProductCatalog


@pytest.fixture(scope="module")
def products() -> ProductCatalog:
    return ProductCatalog.from_file(PROJECT_ROOT / "metadata" / "sources" / "products.json")


class TestProducts:
    def test_four_variables_in_order(self, products):
        assert products.variable_ids == [
            "precipitation",
            "no2",
            "evapotranspiration",
            "temperature",
        ]

    def test_no2_starts_october_2004(self, products):
        assert products.availability("no2")[0] == "2004-10"
        assert not products.is_available("no2", 2004, 9)
        assert products.is_available("no2", 2004, 10)

    def test_imerg_v07_ends_september_2025(self, products):
        assert products.availability("precipitation")[1] == "2025-09"

    def test_common_range_of_all_variables(self, products):
        assert products.common_available_range(products.variable_ids) == ("2004-10", "2025-09")

    def test_every_variable_has_nine_classes(self, products):
        for v in products.variable_ids:
            display = products.get(v)["display"]
            assert len(display["ramp"]) == 9
            assert len(display["breaks"]) == 8
            assert display["breaks"] == sorted(display["breaks"])

    def test_titiler_colormap_uses_file_units(self, products):
        cmap = interval_colormap(products.get("no2")["display"])
        assert len(cmap) == 9
        assert cmap[1][0] == [0.5e15, 1e15]


class TestDemoService:
    def test_variables_report_demo_mode(self, demo_service):
        result = demo_service.variables()
        assert result.mode == "demo"
        assert [v.id for v in result.variables] == [
            "precipitation",
            "no2",
            "evapotranspiration",
            "temperature",
        ]

    def test_layer_is_a_grid_labelled_as_demo(self, demo_service):
        layer = demo_service.layer("precipitation", 2015, 7)
        assert layer.layer.kind == "grid"
        assert layer.quality.flags == ["demo"]
        grid = layer.layer.grid
        assert len(grid.values) == grid.nx * grid.ny
        valid = [v for v in grid.values if v is not None]
        assert valid and min(valid) >= 0

    def test_demo_values_are_deterministic(self, demo_service):
        a = demo_service.point("temperature", 2010, 5, 25.0, -105.0)
        b = demo_service.point("temperature", 2010, 5, 25.0, -105.0)
        assert a.value == b.value is not None

    def test_date_without_data_is_rejected(self, demo_service):
        with pytest.raises(DateUnavailable, match="octubre de 2004"):
            demo_service.layer("no2", 2003, 6)

    def test_point_outside_area_is_rejected(self, demo_service):
        with pytest.raises(InvalidRequest):
            demo_service.point("precipitation", 2015, 7, 45.0, -100.0)

    def test_ocean_point_has_no_value(self, demo_service):
        assert demo_service.point("precipitation", 2015, 7, 20.0, -115.0).value is None

    def test_no2_display_scale(self, demo_service):
        p = demo_service.point("no2", 2015, 1, 19.43, -99.13)
        assert p.value is not None and p.value > 1e15
        assert p.display_value == pytest.approx(p.value / 1e15)

    def test_national_statistics(self, demo_service):
        result = demo_service.statistics("temperature", 2015, 5, None)
        s = result.stats
        assert s.min <= s.median <= s.max
        assert s.min <= s.mean <= s.max
        assert 0.9 < s.coverage <= 1.0
        assert result.region.level == "national"

    def test_state_statistics_use_region_mask(self, demo_service):
        nat = demo_service.statistics("precipitation", 2015, 7, None).stats
        state = demo_service.statistics("precipitation", 2015, 7, "estado:09").stats
        assert 0 < state.n_cells < nat.n_cells

    def test_tiny_municipality_uses_centroid_cell(self, demo_service):
        result = demo_service.statistics("precipitation", 2015, 7, "municipio:09015")
        assert result.stats.n_cells == 1

    def test_regions_unavailable_message(self, demo_service_without_boundaries):
        response = demo_service_without_boundaries.regions_list("state", None)
        assert response.available is False and response.items == []
        with pytest.raises(InvalidRequest):
            demo_service_without_boundaries.statistics("precipitation", 2015, 7, "estado:09")

    def test_timeseries_respects_availability(self, demo_service):
        series = demo_service.timeseries(
            "no2", start="2000-01", end="2005-12", lat=19.43, lon=-99.13
        )
        assert series.points[0].date == "2004-10"
        assert len(series.points) == 15

    def test_regional_series_has_trend_block(self, demo_service):
        series = demo_service.timeseries("temperature", region="estado:26")
        assert series.trend is not None
        assert series.trend.n_years >= 20
        assert 0 <= series.trend.p_value <= 1

    def test_correlation_uses_common_period(self, demo_service):
        result = demo_service.correlation(
            "precipitation", "evapotranspiration", lat=17.0, lon=-93.0
        )
        assert result.start >= "2000-03"
        assert result.n > 100 and -1 <= result.r <= 1
        assert "no indica que una variable cause" in result.note

    def test_compare_two_dates(self, demo_service):
        result = demo_service.compare("precipitation", "2015-01", "2015-07", None)
        assert result.difference_mean > 0  # julio es temporada de lluvias en los datos de demo
        assert 0 <= result.cells_increase_fraction <= 1

    def test_csv_export_is_labelled_demo(self, demo_service):
        text = demo_service.timeseries_csv(
            variable="precipitation", start="2015-01", end="2015-12", lat=17.0, lon=-93.0
        )
        assert "DEMOSTRACIÓN" in text and "SIMULADOS" in text
        assert len([line for line in text.splitlines() if line.startswith("2015-")]) == 12

    def test_raster_download_not_in_demo(self, demo_service):
        with pytest.raises(NotAvailableInMode):
            demo_service.raster_file("precipitation", 2015, 7)


class TestStats:
    def test_weighted_mean(self):
        values = np.array([[1.0, 3.0]])
        weights = np.array([[1.0, 3.0]])
        assert stats.describe(values, weights)["mean"] == pytest.approx(2.5)

    def test_theil_sen_exact_line(self):
        slope, intercept = stats.theil_sen([2000, 2001, 2002, 2003], [1, 3, 5, 7])
        assert slope == pytest.approx(2.0)
        assert intercept == pytest.approx(-3999.0)

    def test_mann_kendall_detects_monotonic_trend(self):
        result = stats.mann_kendall(list(range(20)))
        assert result["p_value"] < 0.001
        flat = stats.mann_kendall([1.0] * 10 + [1.0] * 10)
        assert flat["p_value"] == pytest.approx(1.0)

    def test_anomalies_remove_seasonal_cycle(self):
        dates = [f"{y}-{m:02d}" for y in (2001, 2002) for m in range(1, 13)]
        values = [float(m) for _ in (0, 1) for m in range(1, 13)]
        assert all(abs(a) < 1e-12 for a in stats.monthly_anomalies(dates, values))

    def test_pearson(self):
        r = stats.pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10.5])
        assert r["r"] > 0.99 and r["n"] == 5
        assert stats.pearson([1, None, 3], [1, 2, 3])["r"] is None  # muy pocos pares

    def test_normal_cdf(self):
        assert stats.normal_cdf(0) == pytest.approx(0.5)
        assert stats.normal_cdf(1.96) == pytest.approx(0.975, abs=1e-3)
        assert math.isclose(stats.normal_cdf(-1.0) + stats.normal_cdf(1.0), 1.0)
