# Detectives de Tendencias

Herramienta para el reto **"Be An Earth System Trend Detective!"** del NASA Space Apps Challenge 2026.

El usuario elige una variable de ciencias de la Tierra y una región, ve cómo cambia con el tiempo y descubre si esa tendencia es **significativa**.

## Qué hace

1. **Elegir variable y región**: temperatura, lluvia, humedad del suelo, contaminación…
2. **Mapa de tendencias**: rojo si sube, azul si baja; las zonas con cambio significativo van marcadas.
3. **Clic en una zona**: gráfica de la serie de tiempo y una tarjeta en lenguaje simple con la pendiente y la prueba de Mann-Kendall.
4. **Casos de detective**: 2 o 3 ejemplos guiados para aprender a usar la herramienta.

## Estructura

```
data/raw/         datos descargados de NASA (no se suben a git)
data/processed/   resultados precalculados que lee la app
data/mock/        datos falsos para desarrollar la app sin esperar
src/datos/        Persona 1 · descarga y limpieza
src/analisis/     Persona 2 · tendencias y significancia
app/              Persona 3 · app y mapa
docs/             Persona 4 · definiciones, casos, pitch
```

**El contrato entre todos es [`docs/formato-resultados.md`](docs/formato-resultados.md).** Si alguien necesita cambiarlo, se avisa al equipo primero.

## Cómo correrlo

```bash
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

python src/analisis/tendencias.py    # prueba el análisis con datos sintéticos
streamlit run app/app.py             # abre la app
```

Para descargar datos se necesita una cuenta gratuita de NASA Earthdata: https://urs.earthdata.nasa.gov

## Equipo

| Rol | Persona |
|---|---|
| Datos | _nombre_ |
| Análisis | _nombre_ |
| App y mapa | _nombre_ |
| Contenido y pitch | _nombre_ |

## Cómo trabajamos

- Una rama por persona (`datos`, `analisis`, `app`, `contenido`) y Pull Request a `main`.
- `main` siempre debe funcionar.
- No se suben datos crudos (`data/raw/` está en `.gitignore`).
- Juntas cortas al inicio, en la hora 20 y en la hora 40.

## Fuentes de datos

| Variable | Fuente |
|---|---|
| Temperatura del aire | MERRA-2 |
| Lluvia | GPM IMERG |
| Temperatura de superficie | MODIS |
| Humedad del suelo | GLDAS |
| NO₂ (contaminación) | OMI |
