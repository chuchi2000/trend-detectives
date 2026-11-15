# Data format

This is the agreement between **Data**, **Analysis** and **App**. Everything lives in `data/processed/` and can be rebuilt with two commands (see the README).

```
data/giovanni/                                     original CSV files from Giovanni (do not edit)
data/processed/catalog.json                        available variables and regions
data/processed/<variable>/<region>.csv             clean monthly series (date, value)
data/processed/<variable>/trends.json              results for the map
data/processed/<variable>/series/<region>.json     series for the chart shown on click
data/processed/trends_summary.csv                  everything in one table, for a quick check
```

Variables: `temperature` (°C), `precipitation` (mm/month), `evapotranspiration` (mm/month), `no2` (10¹⁵ molecules/cm²).
Regions: `puebla`, `mexico_city`, `monterrey`, `merida`, `hermosillo`.

## 1. `<region>.csv`: the clean series

```
date,value
2000-01,12.43
2000-02,14.45
```

`no2` also has `valid_days`: how many days had data that month. If fewer than 5, the value is left empty.

## 2. `trends.json`: what the map shows

```json
{
  "variable": "temperature",
  "name": "Air temperature at 2 m",
  "source": "MERRA-2 (M2TMNXSLV v5.12.4)",
  "units": "°C",
  "period": { "start": "2000-01", "end": "2025-12" },
  "regions": [
    {
      "id": "puebla", "name": "Puebla", "lat": 19.04, "lon": -98.2,
      "slope_per_decade": 0.555, "ci95": [0.38, 0.73],
      "sen_slope_per_decade": 0.55,
      "pct_change_per_decade": null,
      "p_value": 0.00003, "t_test_p_value": 0.00001,
      "significant": true, "direction": "increasing",
      "lag1_autocorrelation": 0.45, "effective_months": 118.0,
      "mean": 16.4, "months": 312, "start": "2000-01", "end": "2025-12"
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `slope_per_decade` | how much the variable changes every 10 years, in its `units` (least-squares line) |
| `ci95` | 95 % confidence interval of the slope, corrected for autocorrelation |
| `sen_slope_per_decade` | Sen's slope: median of the slopes between every pair of months; barely affected by outliers |
| `pct_change_per_decade` | the slope as a % of the mean; `null` for temperature, because °C has an arbitrary zero |
| `p_value` | from the Mann-Kendall test, modified for autocorrelation (Hamed and Rao) |
| `t_test_p_value` | from the t-test of the slope, corrected for autocorrelation; should agree with `p_value` |
| `significant` | `true` if `p_value < 0.05` |
| `lag1_autocorrelation` | how much each month resembles the previous one (after removing the trend) |
| `effective_months` | how many independent months the data are worth: `n (1 − r1) / (1 + r1)` |

## 3. `series/<region>.json`: the chart shown on click

```json
{
  "id": "puebla",
  "dates": ["2000-01", "2000-02", "..."],
  "values": [12.43, 14.45, "..."],
  "anomalies": [-0.3, 0.1, "..."]
}
```

- `values`: the monthly data.
- `anomalies`: the same data with the seasonal cycle removed (this is what the trend is computed on).
- A month with no data appears as `null`.
