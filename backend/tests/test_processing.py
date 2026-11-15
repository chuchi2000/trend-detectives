"""Pruebas de la lógica científica del procesamiento (sin descargar nada)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from processing.common import qc
from processing.common.regrid import conservative_regrid, edges_from_centers, overlap_matrix
from processing.common.temporal import (
    composite_length,
    composites_for_month,
    monthly_from_composites,
    overlap_days,
    rate_to_monthly_total,
)
from processing.no2.pipeline import monthly_mean


def modis_starts(year: int) -> list[date]:
    return [date.fromordinal(date(year, 1, 1).toordinal() + 8 * k) for k in range(46)]


class TestComposites:
    def test_last_composite_of_year_is_shorter(self):
        assert composite_length(date(2015, 12, 27)) == 5  # 2015 no es bisiesto
        assert composite_length(date(2016, 12, 26)) == 6  # 2016 sí es bisiesto
        assert composite_length(date(2015, 7, 4)) == 8

    def test_composite_split_between_months(self):
        start = date(2015, 1, 25)  # 25 ene – 1 feb
        assert overlap_days(start, 8, 2015, 1) == 7
        assert overlap_days(start, 8, 2015, 2) == 1

    def test_every_day_of_the_year_is_covered_once(self):
        starts = modis_starts(2015)
        total = sum(
            days for m in range(1, 13) for _, days, _ in composites_for_month(starts, 2015, m)
        )
        assert total == 365

    def test_monthly_sum_of_constant_daily_rate(self):
        # 2 mm por día => cada compuesto de 8 días suma 16 mm; julio debe sumar 62 mm.
        starts = modis_starts(2015)
        values = np.array([[2.0 * composite_length(s)] for s in starts])
        monthly, coverage = monthly_from_composites(values, starts, 2015, 7, "sum", 0.8)
        assert monthly[0] == pytest.approx(62.0)
        assert coverage[0] == pytest.approx(1.0)

    def test_monthly_mean_weights_by_days(self):
        starts = [date(2015, 1, 25), date(2015, 2, 2)]
        values = np.array([[10.0], [20.0]])  # 1 día de febrero vale 10 y 8 días valen 20
        monthly, _ = monthly_from_composites(values, starts, 2015, 2, "mean", 0.0)
        assert monthly[0] == pytest.approx((10 * 1 + 20 * 8) / 9)

    def test_missing_composites_are_not_zero(self):
        starts = modis_starts(2015)
        values = np.array([[2.0 * composite_length(s)] for s in starts])
        values[27] = np.nan  # quita el compuesto del 9 al 16 de agosto
        monthly, coverage = monthly_from_composites(values, starts, 2015, 8, "sum", 0.7)
        assert coverage[0] < 1.0
        assert monthly[0] == pytest.approx(62.0)  # se escala, no se toma como cero

    def test_low_coverage_gives_no_data(self):
        starts = modis_starts(2015)
        values = np.full((len(starts), 1), np.nan)
        values[31] = 16.0  # un solo compuesto válido en septiembre (6–13 sep)
        monthly, coverage = monthly_from_composites(values, starts, 2015, 9, "sum", 0.8)
        assert np.isnan(monthly[0])
        assert coverage[0] == pytest.approx(8 / 30)

    def test_imerg_rate_to_total(self):
        rate = np.array([1.0])
        assert rate_to_monthly_total(rate, 2016, 2)[0] == pytest.approx(24 * 29)


class TestQuality:
    def test_bits(self):
        assert qc.bits(np.array([0b11000101]), 6, 2)[0] == 3
        assert qc.bits(np.array([0b11000101]), 0, 2)[0] == 1

    def test_mod11_filter(self):
        lst = np.array([15000, 15000, 15000, 15000, 0], dtype=np.uint16)
        qcv = np.array(
            [
                0b00000000,  # buena calidad
                0b01000001,  # otra calidad, error ≤ 2 K -> se acepta
                0b11000001,  # otra calidad, error > 3 K -> se descarta
                0b00000010,  # no producido por nubes
                0b00000000,
            ],
            dtype=np.uint8,
        )
        assert qc.mod11_good(lst, qcv).tolist() == [True, True, False, False, False]
        assert qc.lst_to_celsius(np.array([15000]))[0] == pytest.approx(26.85, abs=1e-3)

    def test_mod16_special_values_are_not_et(self):
        raw = np.array([123, 32767, 32766, 32765, 32762, 32761, 0], dtype=np.int16)
        assert qc.mod16_valid(raw).tolist() == [True, False, False, False, False, False, True]
        assert qc.et_to_mm(np.array([123]))[0] == pytest.approx(12.3)

    def test_fill_values(self):
        assert not qc.imerg_valid(np.array([qc.IMERG_FILL]))[0]
        assert not qc.omi_valid(np.array([qc.OMI_FILL], dtype="float32"))[0]
        assert qc.omi_valid(np.array([-1e14]))[0]  # negativos individuales se conservan


class TestRegrid:
    def test_overlap_matrix(self):
        w = overlap_matrix(np.array([0.0, 0.1, 0.2, 0.3]), np.array([0.0, 0.25]))
        assert w[0].tolist() == pytest.approx([0.1, 0.1, 0.05])

    def test_constant_field_is_preserved(self):
        lats = np.arange(19.95, 18.0, -0.1)
        lons = np.arange(-99.95, -98.0, 0.1)
        data = np.full((lats.size, lons.size), 7.0)
        out, frac = conservative_regrid(
            data,
            edges_from_centers(lats),
            edges_from_centers(lons),
            np.arange(20.0, 18.0 - 1e-9, -0.25),
            np.arange(-100.0, -98.0 + 1e-9, 0.25),
        )
        assert np.allclose(out, 7.0)
        assert np.allclose(frac, 1.0)

    def test_nan_cells_are_ignored_and_threshold_applies(self):
        lats = np.array([0.375, 0.125])
        lons = np.array([0.125, 0.375])
        data = np.array([[1.0, np.nan], [np.nan, np.nan]])
        out, frac = conservative_regrid(
            data,
            edges_from_centers(lats),
            edges_from_centers(lons),
            np.array([0.5, 0.0]),
            np.array([0.0, 0.5]),
            min_valid_fraction=0.5,
        )
        assert np.isnan(out[0, 0])  # solo ~25 % del área tiene dato
        out2, _ = conservative_regrid(
            data,
            edges_from_centers(lats),
            edges_from_centers(lons),
            np.array([0.5, 0.0]),
            np.array([0.0, 0.5]),
            min_valid_fraction=0.2,
        )
        assert out2[0, 0] == pytest.approx(1.0)


def test_no2_monthly_mean_requires_min_days():
    daily = np.array([[[1.0, np.nan]], [[3.0, 5.0]], [[np.nan, np.nan]], [[2.0, np.nan]]])
    mean, n = monthly_mean(daily, min_days=2)
    assert mean[0, 0] == pytest.approx(2.0)
    assert np.isnan(mean[0, 1])
    assert n.tolist() == [[3, 1]]


def test_modis_marker_covers(tmp_path):
    import json
    from datetime import date

    from processing.common.modis import MARKER, marker_covers

    assert not marker_covers(tmp_path, date(2015, 6, 24), date(2015, 7, 31))
    (tmp_path / MARKER).write_text(json.dumps({"start": "2015-01-01", "end": "2015-12-31"}))
    assert marker_covers(tmp_path, date(2015, 6, 24), date(2015, 7, 31))
    assert not marker_covers(tmp_path, date(2014, 12, 25), date(2015, 1, 31))
    (tmp_path / MARKER).write_text("no es json")
    assert not marker_covers(tmp_path, date(2015, 6, 24), date(2015, 7, 31))
