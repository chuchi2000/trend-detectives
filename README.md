# Trend Detectives

A tool for the NASA Space Apps Challenge 2026 challenge **"Be An Earth System Trend Detective!"**

Pick an Earth science variable and a region, see how it has changed over time, and find out whether that trend is **statistically significant**.

## What it does

1. **Choose a variable and a region**: air temperature, precipitation, evapotranspiration or air pollution (NO₂).
2. **Trend map**: red where the variable is rising, blue where it is falling; significant trends are highlighted.
3. **Click a region**: see its time series and a plain-language summary with the rate of change and the Mann-Kendall test result.
4. **Detective cases**: 2–3 guided examples that show how to use the tool.

## Current results (2000–2025)

| Region | Air temperature | Precipitation | Evapotranspiration | NO₂ |
|---|---|---|---|---|
| Mexico City | +0.57 °C/decade ✓ | −0.5 %/decade | +3.1 %/decade | **−13.8 %/decade ✓** |
| Hermosillo | +0.47 °C/decade ✓ | −5.9 %/decade | −2.6 %/decade | +3.8 %/decade |
| Mérida | +0.42 °C/decade ✓ | +3.1 %/decade | +3.1 %/decade | +0.7 %/decade |
| Monterrey | +0.42 °C/decade ✓ | +0.9 %/decade | +2.7 %/decade | **+7.0 %/decade ✓** |
| Puebla | +0.56 °C/decade ✓ | −0.4 %/decade | **+3.5 %/decade ✓** | +0.5 %/decade |

✓ = significant (modified Mann-Kendall test, p < 0.05). Precipitation data end in September 2025; NO₂ data start in October 2004.

## Project structure

```
data/giovanni/    original CSV files downloaded from NASA Giovanni (do not edit)
data/processed/   clean series and trend results that the app reads
src/data/         Data · download and cleaning
src/analysis/     Analysis · trends and significance
app/              App and map (Streamlit)
docs/             Content · data format, definitions, cases, pitch
```

**The contract between all roles is [`docs/data-format.md`](docs/data-format.md).** If anyone needs to change it, tell the team first.

## How to run it

```bash
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m streamlit run app/app.py
```

### Rebuild the data

Put the CSV files downloaded from Giovanni in `data/giovanni/`, then run:

```bash
python src/data/clean_giovanni.py data/giovanni   # cleans files and converts units
python src/analysis/analyze_all.py                # computes all trends
```

## Team

| Role | Member |
|---|---|
| Data | _name_ |
| Analysis | _name_ |
| App and map | _name_ |
| Content and pitch | _name_ |

## How we work

- One branch per person (`data`, `analysis`, `app`, `content`) and a pull request into `main`.
- `main` must always work.
- Large raw data stays out of git (`data/raw/` is in `.gitignore`).

## Data sources

All series are area-averaged monthly time series generated with [NASA Giovanni](https://giovanni.gsfc.nasa.gov/giovanni/).

| Variable | Dataset | Resolution |
|---|---|---|
| Air temperature at 2 m | MERRA-2 (M2TMNXSLV v5.12.4) | 0.5° × 0.625°, monthly |
| Precipitation | GPM IMERG Final (GPM_3IMERGM v07) | 0.1°, monthly |
| Evapotranspiration | GLDAS Noah land surface model (GLDAS_NOAH025_M v2.1) | 0.25°, monthly |
| Tropospheric NO₂ | OMI (OMNO2d v004) | 0.25°, daily → monthly mean |

Each region is a 1.5° × 1.5° box (about 160 km per side) centered on the city.
