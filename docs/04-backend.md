# 4. Backend y API

FastAPI + Uvicorn + Pydantic. La documentación interactiva, generada a partir del código,
está en <http://localhost:8000/docs> (Swagger) y <http://localhost:8000/redoc>.

## Capas del backend

```
backend/app/
├── main.py              Crea la app: CORS, manejo de errores, rutas bajo /api
├── core/                config.py (variables de entorno), errors.py, logging.py
├── api/
│   ├── deps.py          Inyección del servicio y tipo VariableId
│   └── routes/          catalog, layers, analysis, regions, export
├── schemas/models.py    Modelos Pydantic de todas las respuestas
└── services/
    ├── atlas.py         AtlasService: toda la lógica, sin depender de FastAPI
    ├── store.py         Protocolo DataStore (de dónde salen los datos)
    ├── demo_store.py    DemoStore: campos SIMULADOS, deterministas
    ├── file_store.py    FileStore: archivos NASA procesados (COG, NetCDF, Zarr)
    ├── catalog.py       Índice de archivos procesados (data/catalog/catalog.json)
    ├── products.py      Lee products.json (disponibilidad, unidades, malla común)
    ├── regions.py       Estados y municipios (GeoJSON del INEGI) y máscaras
    ├── grid.py          Malla común de 0.25° y pesos por área
    ├── stats.py         Estadísticas, Theil–Sen, Mann–Kendall, anomalías, Pearson
    ├── geometry.py      Punto en polígono vectorizado
    ├── colormaps.py     Paletas por intervalos para TiTiler
    └── dates.py         Utilidades de meses
```

**Por qué esta separación**: las rutas solo validan parámetros y llaman a
`AtlasService`. El servicio no sabe si los datos son demo o reales; recibe un `DataStore`.
Así, cambiar `ATLAS_DATA_MODE` cambia la fuente sin tocar la lógica, y las pruebas
pueden ejercitar el servicio sin servidor HTTP.

## Endpoints

Todos son `GET` bajo `/api`. Fechas `AAAA-MM`. Regiones: `nacional`, `estado:24`,
`municipio:24028` (claves del INEGI).

| Ruta | Parámetros | Devuelve |
|---|---|---|
| `/health` | — | Estado, modo (`demo`/`real`), versión, si hay límites cargados |
| `/variables` | — | Las 4 variables con producto, unidades, disponibilidad y meses procesados |
| `/metadata/{variable}` | — | Ficha completa de la auditoría: producto, DOI, capas, QC, método, advertencias |
| `/layers/{variable}` | `year`, `month` | Referencia de la capa del mapa |
| `/precipitation`, `/no2`, `/evapotranspiration`, `/temperature` | `year`, `month` | Atajos de la ruta anterior |
| `/point` | `variable`, `year`, `month`, `lat`, `lon` | Valor en un punto y la celda usada |
| `/statistics` | `variable`, `year`, `month`, `region?` | Media y desviación ponderadas por área, mediana, mín./máx. y dónde, cobertura |
| `/timeseries` | `variable`, `lat`+`lon` o `region`, `start?`, `end?`, `trend?` | Serie mensual + tendencia |
| `/correlation` | `a`, `b`, `lat`+`lon` o `region`, `start?`, `end?` | Pearson sobre anomalías mensuales |
| `/compare` | `variable`, `a`, `b`, `region?` | Estadísticas de dos fechas y su diferencia |
| `/regions` | `level=state\|municipality`, `estado?` | Lista de regiones |
| `/regions/geojson` | `level`, `estado?` | Límites simplificados |
| `/export/timeseries.csv` | como `/timeseries` | CSV |
| `/export/statistics.csv` | como `/statistics` | CSV |
| `/export/raster` | `variable`, `year`, `month` | GeoTIFF (COG) nativo. Solo modo real |

`/api/{variable}?year&month` del plan se implementa como los cuatro atajos y
`/layers/{variable}`; `/api/regions` sirve estados y municipios.

### Forma de una respuesta de capa

```json
{
  "mode": "real",
  "variable": "precipitation",
  "date": "2015-07",
  "unit": "mm/mes",
  "display_unit": "mm/mes",
  "scale": 1.0,
  "resolution": "0.1°",
  "source": "GPM_3IMERGM V07 (NASA GES DISC)",
  "data_type": "…",
  "availability": { "start": "2000-01", "end": "2025-09", "processed": ["2015-07"] },
  "quality": { "flags": [], "coverage": 0.97, "…": "…" },
  "layer": { "kind": "tiles", "tiles": "http://localhost:8001/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?url=…", "…": "…" }
}
```

En modo demo, `layer.kind` es `"grid"` y trae una rejilla de 130 × 76 valores, y
`quality.flags` contiene `"demo"`.

### Errores

Todos los errores tienen la misma forma:

```json
{ "error": { "code": "fecha_sin_datos", "message": "OMI NO₂ empieza en octubre de 2004…" } }
```

| Código | HTTP | Cuándo |
|---|---|---|
| `parametro_invalido` | 422 | Formato de fecha, región o coordenadas inválido |
| `fecha_sin_datos` | 404 | La fecha está fuera de la disponibilidad del producto |
| `sin_procesar` | 404 | El producto sí tiene esa fecha, pero aún no la procesaste |
| `limites_no_cargados` | 404 | Pediste un estado/municipio y no hay límites del INEGI |
| `no_disponible_en_este_modo` | 409 | Por ejemplo, descargar GeoTIFF en modo demo |
| `faltan_librerias_geoespaciales` | 503 | Modo real sin el extra `geo` instalado |

## Métodos estadísticos

- **Media y desviación**: ponderadas por el área de cada celda (∝ cos latitud), porque en
  una malla en grados las celdas del norte son más pequeñas que las del sur.
- **Región**: celdas de 0.25° cuyo centro cae dentro del polígono. Si la región es tan
  pequeña que no contiene ningún centro (muchos municipios), se usa la celda que contiene
  su centroide; el número de celdas usadas aparece en las estadísticas de la respuesta.
- **Serie regional**: un mes cuenta solo si al menos el 50 % del área tiene dato.
- **Tendencia**: pendiente de Theil–Sen sobre medias anuales (año válido con ≥ 9 meses;
  se exigen ≥ 8 años), **prueba de Mann–Kendall corregida por autocorrelación** e
  **intervalo de confianza del 95 %** de la pendiente. Veredicto: «Tendencia sólida»
  (p < 0.05 y el intervalo no incluye el cero), «Indicio, no concluyente» o «No se
  distingue de la variabilidad natural». Fórmulas, validación y referencias en
  [`metadata/documentation/metodos-estadisticos.md`](../metadata/documentation/metodos-estadisticos.md).
- **Correlación**: Pearson sobre anomalías (se resta el ciclo estacional medio de cada
  mes) para no confundir «ambas suben en verano» con una relación. Valor p e intervalo de
  confianza del 95 % por z de Fisher, con tamaño de muestra efectivo por autocorrelación.
- Los datos faltantes nunca se tratan como cero.

## Configuración

Variables de entorno (archivo `.env` en la raíz):

| Variable | Por defecto | Uso |
|---|---|---|
| `ATLAS_DATA_MODE` | `demo` | `demo` o `real` |
| `ATLAS_DATA_DIR` | `<raíz>/data` | Carpeta de datos |
| `ATLAS_METADATA_DIR` | `<raíz>/metadata` | Carpeta de metadatos |
| `ATLAS_CORS_ORIGINS` | `http://localhost:5173` | Orígenes permitidos, separados por coma |
| `TITILER_URL` | `http://localhost:8001` | URL de TiTiler vista desde el navegador |
| `TITILER_DATA_DIR` | `/data` | Ruta de `data/` dentro del contenedor de TiTiler |
| `ATLAS_LOG_LEVEL` | `INFO` | Nivel de registro |

## Registro (logging)

Cada petición con error queda en el registro con su código. Los errores inesperados se
registran con traza completa y el cliente recibe un 500 genérico sin detalles internos.

## Pruebas

```bash
cd backend && pytest
```

- `test_processing.py`: compuestos de 8 días repartidos por mes, conversión de unidades,
  filtros QC, re-malla conservativa, mínimos de cobertura.
- `test_trend_statistics.py`: intervalo de Sen, veredictos con series simuladas
  (ruido, ruido con memoria, tendencias reales) y correlación con tamaño efectivo.
- `test_services.py`: disponibilidad de productos, paletas, estadísticas, tendencias,
  regiones y el servicio completo en modo demo. (Falta: pruebas del `FileStore` con un
  COG y un cubo pequeños, y del catálogo.)
- `test_api.py`: rutas HTTP con `TestClient` (necesita FastAPI y httpx, incluidos en `dev`).

## PostgreSQL / PostGIS

Por ahora el catálogo es un JSON y los límites son GeoJSON: es suficiente para 4 variables
× ~310 meses y evita mantener una base de datos desde el día uno. Los píxeles **nunca** se
guardan en tablas: viven en COG/NetCDF/Zarr. Cuando se necesiten consultas espaciales
complejas o muchos usuarios, `docker-compose.yml` ya incluye PostGIS (perfil `postgis`) y
la clase `Catalog` es el único punto que habría que cambiar.
