# Atlas Ambiental de México

Plataforma web para explorar cuatro variables ambientales de satélite sobre todo
México, mes a mes, entre 2000 y 2025:

| Variable | Producto NASA | Unidad mensual | Disponible |
|---|---|---|---|
| Precipitación | GPM IMERG Final Monthly (GPM_3IMERGM) V07 | mm/mes | 2000-01 → 2025-09 |
| Dióxido de nitrógeno (NO₂) | OMI/Aura OMNO2d V004 (columna troposférica) | molec/cm² | 2004-10 → 2025-12 |
| Evapotranspiración | MODIS/Terra MOD16A2GF v061 | mm/mes | 2000-03 → 2025-12 |
| Temperatura de superficie (LST diurna) | MODIS/Terra MOD11A2 v061 | °C | 2000-03 → 2025-12 |

Las fechas salen de la auditoría de productos (`metadata/sources/products.json` y
`metadata/documentation/auditoria-productos.md`). **No todas las variables empiezan en
enero de 2000**, y el periodo común para comparar las cuatro es **2004-10 → 2025-09**.

Tiene dos modos que comparten el mismo mapa, fecha, variable y lugar:

- **Explorador**: para estudiantes y público general. Lenguaje claro, preguntas guía,
  glosario y datos curiosos con fuente.
- **Científico**: estadísticas por región, series con tendencia (Theil–Sen + Mann–Kendall),
  correlaciones, comparación de fechas, metadatos completos y exportaciones.

Cambiar de modo no reinicia la consulta: el estado vive en la URL
(`/atlas?modo=cientifico&variable=no2&fecha=2015-07&region=estado:09`).

## Datos de demostración y datos reales

La API arranca por defecto en **modo DEMO**: genera campos **simulados** para poder
desarrollar la interfaz sin descargar nada. No son mediciones. Se identifican siempre:

- `/api/health` y todas las respuestas llevan `"mode": "demo"`.
- La interfaz muestra una franja permanente «Datos de demostración».
- Los CSV exportados empiezan con una línea de advertencia.

Con `ATLAS_DATA_MODE=real` la API lee solo los archivos procesados de NASA registrados
en `data/catalog/catalog.json`. Si un mes no está procesado, responde 404 con un mensaje
claro; nunca rellena con datos inventados ni con ceros.

## Estructura

```
Mexico_Environmental_Atlas/
├── frontend/          React + TypeScript + Vite + Tailwind + MapLibre + Plotly
├── backend/
│   ├── app/           API FastAPI (rutas, esquemas Pydantic, servicios)
│   ├── processing/    Descarga y procesamiento NASA (una carpeta por variable)
│   └── tests/         Pruebas pytest
├── data/              raw → processed → optimized, límites y catálogo (no se sube a Git)
├── metadata/          Auditoría de productos, calidad y documentación científica
├── docs/              Guías (instalación, ejecución, frontend, backend, NASA…)
├── scripts/           Utilidades sueltas
├── notebooks/         Cuadernos de exploración
├── docker-compose.yml TiTiler (teselas COG) y PostGIS (etapa futura)
└── PROJECT_STATUS.md  Qué está hecho, qué falta y qué está probado
```

## Inicio rápido (modo DEMO)

Requisitos: Python 3.11+, Node.js 20.19+ (o 22.12+) y Git. Detalle en
[`docs/01-instalacion.md`](docs/01-instalacion.md).

```bash
# 1. Configuración
cp .env.example .env

# 2. Backend (terminal 1)
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# 3. Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

Abre <http://localhost:5173>. La documentación interactiva de la API está en
<http://localhost:8000/docs>.

## Guías

1. [Instalación](docs/01-instalacion.md)
2. [Ejecución](docs/02-ejecucion.md)
3. [Frontend](docs/03-frontend.md)
4. [Backend y API](docs/04-backend.md)
5. [Procesamiento NASA](docs/05-procesamiento-nasa.md)
6. [Agregar una variable nueva](docs/06-agregar-variables.md)
7. [Cuenta Earthdata y credenciales](docs/07-earthdata.md)
8. [VS Code: extensiones y configuración](docs/08-vscode.md)
9. [Auditoría de productos](metadata/documentation/auditoria-productos.md)

## Seguridad

- Las credenciales de NASA solo las usan los scripts de `backend/processing`, leídas de
  variables de entorno o de `~/.netrc`. **Nunca** van en el frontend.
- `.env` y `.netrc` están en `.gitignore`. Comparte solo `.env.example`.
- La API solo acepta `GET`, valida todos los parámetros y nunca envía NetCDF completos al
  navegador: entrega estadísticas, series, rejillas pequeñas o teselas.

## Créditos de datos

Cita cada producto con su DOI (están en `metadata/sources/products.json`). Límites
estatales y municipales: Marco Geoestadístico del INEGI. Mapa base: OpenFreeMap /
OpenStreetMap.
