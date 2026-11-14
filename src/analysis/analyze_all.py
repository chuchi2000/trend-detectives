"""Runs the trend analysis on every clean series. (Analysis role)

Usage (after cleaning the data):
    python src/analysis/analyze_all.py

Reads data/processed/<variable>/<region>.csv and writes:
  - data/processed/<variable>/trends.json             → what the map shows
  - data/processed/<variable>/series/<region>.json    → the chart shown on click
  - data/processed/trends_summary.csv                 → one table for a quick check
"""

import json
from pathlib import Path

import pandas as pd

from trends import analyze_trend, remove_seasonality

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed"


def read_series(path: Path) -> pd.Series:
    table = pd.read_csv(path)
    return pd.Series(table["value"].values, index=pd.to_datetime(table["date"]))


def main():
    catalog = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))
    rows = []

    for variable, var_info in catalog["variables"].items():
        regions = []
        for path in sorted((DATA / variable).glob("*.csv")):
            region = path.stem
            reg_info = catalog["regions"][region]
            series = read_series(path)
            r = analyze_trend(series)

            regions.append({"id": region, "name": reg_info["name"],
                            "lat": reg_info["lat"], "lon": reg_info["lon"], **r})

            anomalies = remove_seasonality(series.dropna()).reindex(series.index)
            target = DATA / variable / "series" / f"{region}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps({
                "id": region,
                "dates": [f"{d:%Y-%m}" for d in series.index],
                "values": [None if pd.isna(v) else round(float(v), 4) for v in series.values],
                "anomalies": [None if pd.isna(v) else round(float(v), 4) for v in anomalies.values],
            }, ensure_ascii=False), encoding="utf-8")

            rows.append({"variable": variable, "region": reg_info["name"],
                         "units": var_info["units"], **{k: v for k, v in r.items() if k != "ci95"},
                         "ci95_low": r["ci95"][0], "ci95_high": r["ci95"][1]})

        period = {"start": min(z["start"] for z in regions), "end": max(z["end"] for z in regions)}
        (DATA / variable / "trends.json").write_text(json.dumps({
            "variable": variable, **var_info, "period": period, "regions": regions,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = pd.DataFrame(rows)
    summary.to_csv(DATA / "trends_summary.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(summary[["variable", "region", "slope_per_decade", "units",
                       "pct_change_per_decade", "p_value", "significant"]].to_string(index=False))


if __name__ == "__main__":
    main()
