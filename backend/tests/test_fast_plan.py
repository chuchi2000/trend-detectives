"""Planeación del modo rápido (sin Earth Engine ni Harmony)."""

from __future__ import annotations

from datetime import date

import pytest

from processing.fast import plan
from processing.fast.earth_engine import grid_for


def test_map_grid_covers_mexico_and_aligns_with_comparative_cells():
    grid = plan.aligned_grid(0.025)
    assert (grid.west, grid.north) == (-118.75, 33.25)
    assert (grid.width, grid.height) == (1300, 760)
    assert grid.east == pytest.approx(-86.25) and grid.south == pytest.approx(14.25)
    assert round(0.25 / grid.res, 9) == 10  # 10 × 10 celdas de mapa por celda comparativa


def test_imerg_grid_is_native_0p1_without_resampling():
    grid = grid_for("precipitation", 0.025)
    assert grid.res == 0.1
    assert (grid.west, grid.north) == (-118.8, 33.3)
    assert (grid.width, grid.height) == (326, 191)  # igual al recorte que dio el archivo real


def test_requests_stay_under_earth_engine_limit():
    small = plan.aligned_grid(0.025)
    assert small.tile_rows(n_bands=2) == [(0, 760)]
    native_et = plan.aligned_grid(1 / 240)
    tiles = native_et.tile_rows(n_bands=2)
    assert sum(rows for _, rows in tiles) == native_et.height
    assert all(native_et.width * rows * 2 * 4 <= plan.MAX_REQUEST_BYTES for _, rows in tiles)
    assert native_et.affine(tiles[1][0])["translateY"] < native_et.north


def test_finer_than_native_is_refused():
    with pytest.raises(ValueError, match="inventar detalle"):
        grid_for("temperature", 0.005)


def test_composites_plan_matches_classic_rule():
    starts = [
        date(2015, 6, 26),
        date(2015, 7, 4),
        date(2015, 7, 12),
        date(2015, 7, 20),
        date(2015, 7, 28),
        date(2015, 8, 5),
    ]
    uses = plan.composites_plan(starts, 2015, 7)
    assert [(u.start.day, u.days_in_month, u.length) for u in uses] == [
        (26, 3, 8),
        (4, 8, 8),
        (12, 8, 8),
        (20, 8, 8),
        (28, 4, 8),
    ]
    assert sum(u.days_in_month for u in uses) == 31
    last = plan.composites_plan([date(2015, 12, 27)], 2015, 12)
    assert last[0].length == 5  # el último compuesto del año es más corto


def test_months_between_and_search_window():
    assert plan.months_between("2024-11", "2025-02") == [
        (2024, 11),
        (2024, 12),
        (2025, 1),
        (2025, 2),
    ]
    assert plan.composite_search_window(2015, 12) == (date(2015, 11, 24), date(2016, 1, 1))


def test_harmony_files_are_grouped_by_month(monkeypatch, tmp_path):
    import numpy as np

    from processing.fast import harmony_no2

    names = [
        "467282828_OMNO2d.004_OMI-Aura_L3-OMNO2d_2015m0630_v004-2025m1015t164231_subsetted.nc4",
        "467282829_OMNO2d.004_OMI-Aura_L3-OMNO2d_2015m0701_v004-2025m1015t164231_subsetted.nc4",
        "467282830_OMNO2d.004_OMI-Aura_L3-OMNO2d_2015m0702_v004-2025m1015t164231_subsetted.nc4",
        # el mismo 2 de julio, descargado otra vez en una segunda solicitud:
        "467299999_OMNO2d.004_OMI-Aura_L3-OMNO2d_2015m0702_v004-2025m1015t164231_subsetted.nc4",
    ]
    files = [tmp_path / n for n in names]
    for f in files:
        f.write_bytes(b"")
    grid = np.ones((76, 130), dtype="float32")
    monkeypatch.setattr(
        harmony_no2, "read_subset_file", lambda p: (grid, np.arange(76.0), np.arange(130.0))
    )
    written: dict[str, int] = {}
    monkeypatch.setattr(
        harmony_no2.no2,
        "write_month_subset",
        lambda out, days, layers, *a: written.__setitem__(out.name, len(days)) or out,
    )
    out = harmony_no2.assemble_months(files, tmp_path, "004", 2015, [6, 7, 8])
    assert written == {"OMNO2d_004_mexico_2015-06.nc": 1, "OMNO2d_004_mexico_2015-07.nc": 2}
    assert len(out) == 2  # agosto no tiene días: queda sin dato, no en cero


def test_no2_months_respect_availability():
    from processing.fast import harmony_no2

    by_year = harmony_no2._months_by_year("2004-08", "2005-01")
    assert by_year == {2004: [10, 11, 12], 2005: [1]}


def test_blocks_split_on_memory_errors_and_reassemble_in_place(monkeypatch):
    import sys
    import types

    import numpy as np

    from processing.fast import earth_engine as gee

    grid = plan.aligned_grid(0.025)
    calls = {"ok": 0, "memory": 0}

    def compute_pixels(request):
        dims = request["grid"]["dimensions"]
        aff = request["grid"]["affineTransform"]
        width, height = dims["width"], dims["height"]
        if width * height > 100 * 100:
            calls["memory"] += 1
            raise Exception("User memory limit exceeded.")
        calls["ok"] += 1
        col0 = round((aff["translateX"] - grid.west) / grid.res)
        row0 = round((grid.north - aff["translateY"]) / grid.res)
        rows, cols = np.mgrid[row0 : row0 + height, col0 : col0 + width]
        out = np.zeros((height, width), dtype=[("value", "f4"), ("fraction", "f4")])
        out["value"] = rows * 10_000 + cols
        out["fraction"] = 1
        return out

    fake_ee = types.SimpleNamespace(data=types.SimpleNamespace(computePixels=compute_pixels))
    monkeypatch.setitem(sys.modules, "ee", fake_ee)
    value, fraction = gee.compute_pixels("expresion", grid, tile=256)
    rows, cols = np.mgrid[0 : grid.height, 0 : grid.width]
    assert np.array_equal(value, (rows * 10_000 + cols).astype("float32"))
    assert fraction.min() == 1
    assert calls["memory"] > 0 and calls["ok"] > 0


def test_paused_harmony_job_is_resumed(monkeypatch):
    from processing.fast import harmony_no2

    class FakeClient:
        def __init__(self):
            self.states = ["paused", "successful"]
            self.resumed = 0

        def wait_for_processing(self, job_id, show_progress=True):
            pass

        def status(self, job_id):
            return {"status": self.states[0], "message": ""}

        def resume(self, job_id):
            self.resumed += 1
            self.states.pop(0)

    monkeypatch.setattr(harmony_no2.time, "sleep", lambda s: None)
    client = FakeClient()
    assert harmony_no2._wait_until_done(client, "job", 2006) == "successful"
    assert client.resumed == 1
