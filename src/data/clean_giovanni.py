"""Cleans CSV files downloaded from Giovanni (Time Series, Area-Averaged). (Data role)

Usage:
    python src/data/clean_giovanni.py data/giovanni

For each file it:
  - Detects the variable (from the column name) and the region (from the
    "User Bounding Box" in the header).
  - Removes fill values and converts units.
  - Turns daily data (NO2) into monthly means.
  - Saves data/processed/<variable>/<region>.csv with columns date,value
    and updates data/processed/catalog.json.
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "data" / "processed"

# Demo regions: (west, south, east, north) plus a center point for the map
REGIONS = {
    "puebla":      {"name": "Puebla",      "bbox": (-98.95, 18.30, -97.45, 19.80), "lat": 19.04, "lon": -98.20},
    "mexico_city": {"name": "Mexico City", "bbox": (-99.90, 18.70, -98.40, 20.20), "lat": 19.43, "lon": -99.13},
    "monterrey":   {"name": "Monterrey",   "bbox": (-101.05, 24.90, -99.55, 26.40), "lat": 25.67, "lon": -100.31},
    "merida":      {"name": "Mérida",      "bbox": (-90.40, 19.90, -88.90, 21.30), "lat": 20.97, "lon": -89.62},
    "hermosillo":  {"name": "Hermosillo",  "bbox": (-111.70, 28.30, -110.20, 29.80), "lat": 29.07, "lon": -110.96},
}


def _kelvin_to_celsius(series):
    return series - 273.15


def _mm_per_hour_to_mm_per_month(series):
    # Monthly IMERG is a mean rate in mm/hr: multiply by the hours in each month
    return series * 24 * series.index.days_in_month


def _scale_no2(series):
    return series / 1e15


VARIABLES = {
    "M2TMNXSLV_5_12_4_T2M": {
        "variable": "temperature", "name": "Air temperature at 2 m",
        "source": "MERRA-2 (M2TMNXSLV v5.12.4)", "units": "°C",
        "convert": _kelvin_to_celsius, "daily": False,
    },
    "GPM_3IMERGM_07_precipitation": {
        "variable": "precipitation", "name": "Precipitation",
        "source": "GPM IMERG Final (GPM_3IMERGM v07)", "units": "mm/month",
        "convert": _mm_per_hour_to_mm_per_month, "daily": False,
    },
    "OMNO2d_004_ColumnAmountNO2TropCloudScreened": {
        "variable": "no2", "name": "Tropospheric NO₂ (air pollution)",
        "source": "OMI (OMNO2d v004)", "units": "10¹⁵ molecules/cm²",
        "convert": _scale_no2, "daily": True,
    },
}

MIN_DAYS_PER_MONTH = 5  # for daily data: months with fewer valid days are left empty


def read_giovanni(path: Path):
    """Splits the Giovanni header from the data table."""
    meta, rows, in_data, column = {}, [], False, None
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row:
                continue
            if not in_data:
                if row[0].strip() == "time":
                    in_data, column = True, row[1].strip()
                else:
                    meta[row[0].strip().rstrip(":")] = row[1].strip() if len(row) > 1 else ""
            else:
                rows.append((row[0].strip(), row[1].strip()))
    series = pd.Series(
        pd.to_numeric([v for _, v in rows], errors="coerce"),
        index=pd.to_datetime([t for t, _ in rows]),
    )
    return meta, column, series


def find_region(bbox_text: str):
    bbox = tuple(float(x) for x in bbox_text.split(","))
    for key, region in REGIONS.items():
        if np.allclose(bbox, region["bbox"], atol=0.01):
            return key
    return None


def clean(path: Path):
    meta, column, series = read_giovanni(path)
    var_key = column.removeprefix("mean_")
    if var_key not in VARIABLES:
        print(f"  ⚠ Unknown variable ({var_key}), skipping: {path.name}")
        return None
    var = VARIABLES[var_key]

    region = find_region(meta.get("User Bounding Box", ""))
    if region is None:
        print(f"  ⚠ Unknown region ({meta.get('User Bounding Box')}), skipping: {path.name}")
        return None

    # Remove fill values
    fill = float([v for k, v in meta.items() if k.startswith("Fill Value")][0])
    series = series.where(~np.isclose(series, fill, rtol=1e-6) & (series.abs() < 1e20))

    # Daily -> monthly
    valid_days = None
    if var["daily"]:
        valid_days = series.resample("MS").count()
        series = series.resample("MS").mean().where(valid_days >= MIN_DAYS_PER_MONTH)

    series = var["convert"](series)

    target = OUTPUT / var["variable"] / f"{region}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame({"date": series.index.strftime("%Y-%m"), "value": series.round(4).values})
    if valid_days is not None:
        table["valid_days"] = valid_days.values
    table.to_csv(target, index=False)

    valid = series.dropna()
    print(f"  ✓ {var['variable']:<13} {region:<12} {valid.index.min():%Y-%m} to {valid.index.max():%Y-%m} "
          f"({len(valid)} months) → {target.relative_to(ROOT)}")
    return var["variable"], region, var_key


def main(paths):
    catalog = {"variables": {}, "regions": {}}
    catalog_path = OUTPUT / "catalog.json"
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    for path in paths:
        result = clean(Path(path))
        if result is None:
            continue
        variable, region, var_key = result
        v = VARIABLES[var_key]
        catalog["variables"][variable] = {k: v[k] for k in ("name", "source", "units")}
        catalog["regions"][region] = {k: REGIONS[region][k] for k in ("name", "lat", "lon")} | {
            "bbox": list(REGIONS[region]["bbox"])}

    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Catalog updated: {catalog_path.relative_to(ROOT)}")


def expand(arguments):
    """Accepts files, folders or patterns (*.csv); Windows shells don't expand patterns."""
    paths = []
    for arg in arguments:
        p = Path(arg)
        if p.is_dir():
            paths += sorted(p.glob("*.csv"))
        elif any(c in arg for c in "*?["):
            paths += sorted(Path().glob(arg))
        else:
            paths.append(p)
    return paths


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python src/data/clean_giovanni.py data/giovanni")
    main(expand(sys.argv[1:]))
