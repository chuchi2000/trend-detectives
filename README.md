# Atlas Ambiental de México

Plataforma web que convierte observaciones satelitales de **NASA** en mapas, estadísticas y
**tendencias con significancia estadística** de cuatro variables ambientales para todo
México, mes a mes, entre 2000 y 2025. Disponible en **español e inglés**.

| Variable | Producto NASA | Unidad mensual | Disponible |
|---|---|---|---|
| Precipitación | GPM IMERG Final Monthly (GPM_3IMERGM) V07 | mm/mes | 2000-01 → 2025-09 |
| Dióxido de nitrógeno (NO₂) | OMI/Aura OMNO2d V004 (columna troposférica) | molec/cm² | 2004-10 → 2025-12 |
| Evapotranspiración | MODIS/Terra MOD16A2GF v061 | mm/mes | 2000-03 → 2025-12 |
| Temperatura de superficie (LST diurna) | MODIS/Terra MOD11A2 v061 | °C | 2000-03 → 2025-12 |

**No todas las variables empiezan en enero de 2000.** El periodo en que las cuatro tienen
datos es **2004-10 → 2025-09**. Las fechas salen de la auditoría de productos
(`metadata/sources/products.json`).

---

## Contenido

1. [Qué hace](#1-qué-hace)
2. [Cómo funciona](#2-cómo-funciona)
3. [Requisitos](#3-requisitos)
4. [Ejecutarlo en 10 minutos (modo DEMO)](#4-ejecutarlo-en-10-minutos-modo-demo)
5. [Usar los datos reales de NASA](#5-usar-los-datos-reales-de-nasa)
6. [Recorrido sugerido para revisar el proyecto](#6-recorrido-sugerido-para-revisar-el-proyecto)
7. [Pruebas](#7-pruebas)
8. [Estructura del repositorio](#8-estructura-del-repositorio)
9. [Problemas frecuentes](#9-problemas-frecuentes)
10. [Limitaciones conocidas](#10-limitaciones-conocidas)
11. [Más documentación, seguridad y créditos](#11-más-documentación-seguridad-y-créditos)

---

## 1. Qué hace

La plataforma tiene dos modos que comparten el mismo mapa, variable, fecha y lugar:

- **Explorador** (estudiantes y público general): lenguaje claro, preguntas guía, glosario
  y datos curiosos con fuente.
- **Científico** (universidades e investigación): estadísticas por estado y municipio,
  series de tiempo, tendencias con pruebas estadísticas, correlaciones entre variables,
  comparación de fechas, metadatos completos y exportación en CSV y GeoTIFF.

Funciones principales:

- **Mapa mensual** de cada variable, recortado al contorno de México.
- **Mapa de tendencia** (botón «Tendencia»): cambio por década de cada celda de 0.25°. Rojo
  indica que sube, azul que baja y los colores tenues marcan cambios no significativos.
  Se calcula en tiempo real en menos de 1 segundo.
- **Análisis de un punto o región:** al hacer clic se muestra una frase sencilla, un
  veredicto («Tendencia sólida», «Indicio» o «Variabilidad natural») y la gráfica de
  anomalías con su recta de tendencia.
- **Idioma:** selector **ES / EN** en el encabezado. La API también responde en inglés
  con `?lang=en`.
- **Enlaces compartibles:** el estado completo vive en la URL, por ejemplo
  `/atlas?modo=cientifico&variable=no2&fecha=2015-07&vista=tendencia&lang=en`.

## 2. Cómo funciona

```
NASA (GES DISC, LP DAAC)  ──►  procesamiento (backend/processing)  ──►  data/  ──►  API FastAPI  ──►  React + MapLibre
 IMERG · OMI · MODIS            calidad, unidades, mes, malla 0.25°      cubos y      (backend/app)      (frontend/)
                                                                          mapas
```

**Procesamiento de los datos** (detalle en [docs/05-procesamiento-nasa.md](docs/05-procesamiento-nasa.md)):

1. **Limpieza por calidad.** Se eliminan los valores de relleno y las banderas de mala
   calidad. Un dato faltante **nunca** se convierte en cero: se muestra como «sin dato».
2. **Conversión de unidades.** Por ejemplo: mm/h → mm/mes; K → °C; NO₂ en 10¹⁵ molec/cm².
3. **Agregación a meses.** NO₂ es diario y MODIS viene en compuestos de 8 días; ambos se
   llevan a meses con reglas de cobertura mínima.
4. **Malla común de 0.25°** (130 × 76 celdas) para comparar las cuatro variables. Se usa
   un promedio conservativo ponderado por área, sin inventar más detalle del que tienen
   los datos.

**Modelos matemáticos:**

| Para qué | Método |
|---|---|
| Estadísticas por región | Promedio y desviación ponderados por área (cos φ); mediana, mínimo y máximo por celda |
| Tendencia mensual (principal) | Anomalías (se quita el ciclo estacional) → pendiente por mínimos cuadrados → error estándar, IC 95 % y prueba t corregidos con el tamaño de muestra efectivo n_eff = n(1 − r₁)/(1 + r₁) → pendiente de Sen → Mann–Kendall con modificación de Hamed y Rao |
| Mapa de tendencia | Lo mismo, vectorizado con NumPy para las ~9 900 celdas a la vez |
| Tendencia anual (complementaria) | Theil–Sen sobre promedios anuales + Mann–Kendall corregido + IC de Sen (1968) |
| Correlación | Pearson sobre anomalías, con n efectivo (Bretherton et al., 1999) y z de Fisher |

Código: `backend/app/services/trend_monthly.py`, `trend_map.py` y `stats.py`. Métodos
explicados en [metadata/documentation/metodos-estadisticos.md](metadata/documentation/metodos-estadisticos.md).

## 3. Requisitos

| Programa | Versión | Comprobar |
|---|---|---|
| Git | cualquiera reciente | `git --version` |
| Python | **3.11 o superior** | `python --version` (Windows: también `py --version`) |
| Node.js | **20.19+ o 22.12+** | `node --version` |

- Conexión a internet: el mapa base (OpenFreeMap) se carga en línea.
- No hace falta Docker, base de datos ni cuentas de NASA para el modo DEMO.

## 4. Ejecutarlo en 10 minutos (modo DEMO)

El modo DEMO funciona **recién clonado**, sin descargar datos. Usa campos **simulados**
para mostrar toda la interfaz. La app lo indica con una franja amarilla y cada respuesta de
la API lleva `"mode": "demo"`. Para ver datos reales de NASA, sigue la
[sección 5](#5-usar-los-datos-reales-de-nasa).

### Paso 1. Clonar y configurar

**Windows (PowerShell):**
```powershell
git clone https://github.com/chuchi2000/trend-detectives.git
cd trend-detectives
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
git clone https://github.com/chuchi2000/trend-detectives.git
cd trend-detectives
cp .env.example .env
```

> Si el Atlas todavía no está en la rama `main`, clona la rama del equipo:
> `git clone -b Rochatech https://github.com/chuchi2000/trend-detectives.git`.
> Comprueba que estás en el proyecto correcto: deben existir las carpetas `backend/` y
> `frontend/`.

No hace falta editar `.env`: por defecto trae `ATLAS_DATA_MODE=demo`.

### Paso 2. Backend (terminal 1)

**Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

> Si PowerShell no deja activar el entorno («running scripts is disabled»), ejecuta una
> sola vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a intentarlo.

**macOS / Linux:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Deja esta terminal abierta. Comprueba en el navegador
<http://localhost:8000/api/health>: debe responder `"status": "ok"` y `"mode": "demo"`.

### Paso 3. Frontend (terminal 2, nueva)

```bash
cd frontend
npm install
npm run dev
```

Deja esta terminal abierta también.

### Paso 4. Abrir la app

- Aplicación: <http://localhost:5173>
- Documentación interactiva de la API (Swagger): <http://localhost:8000/docs>

**Las dos terminales deben seguir abiertas.** Si cierras la del backend, la app mostrará
«No se pudo conectar con el servidor del Atlas».

### Paso 5 (opcional). Estados y municipios del INEGI

El selector de región y los contornos estatales necesitan los límites del INEGI. Se
descargan del servicio web oficial en unos minutos, sin cuenta. En la terminal 1, detén la
API con `Ctrl + C` y ejecuta (con el entorno activo, dentro de `backend/`):

```bash
python -m processing.cli limites
uvicorn app.main:app --reload --port 8000
```

## 5. Usar los datos reales de NASA

La carpeta `data/` **no está en el repositorio** (está en `.gitignore`): los archivos
procesados pesan alrededor de 2 GB y se pueden regenerar. Hay dos caminos.

### Opción A. Paquete de datos del equipo (rápido)

Si el equipo te compartió el paquete de datos procesados:

1. Descomprímelo en la raíz del proyecto de modo que quede esta estructura:
   ```
   data/
   ├── catalog/catalog.json
   ├── processed/comparative/        (cubos de 0.25°: tendencias, series, estadísticas)
   ├── processed/monthly/            (NetCDF mensual)
   ├── optimized/cog/                (mapas mensuales)
   └── boundaries/                   (límites del INEGI)
   ```
2. Sigue los pasos de «Activar el modo real» (abajo).

### Opción B. Regenerar los datos (2 a 3 horas)

Requiere una cuenta gratuita de **NASA Earthdata** y una de **Google Earth Engine** (uso no
comercial). Guía completa: [docs/09-descarga-rapida.md](docs/09-descarga-rapida.md). En
resumen, en `backend/` con el entorno activo:

```bash
# Credenciales en .env (raíz): EARTHDATA_USERNAME, EARTHDATA_PASSWORD y EE_PROJECT
pip install -e ".[processing,rapido,dev]"
python -m processing.cli ee-login                            # autoriza Google Earth Engine
python -m processing.cli rapido --inicio 2015-07 --fin 2015-07   # prueba con un mes
python -m processing.cli rapido --inicio 2004-01 --fin 2025-12   # todo el periodo
python -m processing.cli limites                             # límites del INEGI
```

Si se corta, repite el mismo comando: se salta lo que ya está hecho.

### Activar el modo real

1. Instala las librerías geoespaciales (en `backend/`, con el entorno activo):
   ```bash
   pip install -e ".[geo,dev]"
   ```
2. En `.env` (raíz), cambia `ATLAS_DATA_MODE=demo` por `ATLAS_DATA_MODE=real`. Deja
   `ATLAS_MAP_MODE=imagen`: así no se necesita Docker.
3. Reinicia la API (`Ctrl + C` y otra vez `uvicorn app.main:app --reload --port 8000`).
4. Comprueba que <http://localhost:8000/api/health> diga `"mode": "real"`.

Qué necesita cada función:

| Función | Archivos necesarios |
|---|---|
| Mapa de un mes | `data/optimized/cog/<variable>/` |
| Tendencias, series, estadísticas, correlación, comparación | `data/processed/comparative/` |
| Estados, municipios y recorte del mapa al país | `data/boundaries/` |

Si falta algo, la API responde con un mensaje que dice exactamente qué falta y qué
comando lo genera. Nunca rellena con datos inventados.

## 6. Recorrido sugerido para revisar el proyecto

1. **Portada:** cambia el idioma con **ES / EN** y entra a «Análisis científico».
2. **Mapa mensual:** elige NO₂, julio de 2015. Busca las ciudades (Ciudad de México,
   Monterrey, Guadalajara).
3. **Tendencia:** pulsa «Tendencia». Debajo del mapa aparece qué porcentaje del país sube o
   baja de forma significativa.
4. **Un punto:** haz clic sobre la Ciudad de México. El panel muestra la frase, el veredicto,
   la gráfica de anomalías y todas las cifras (pendiente, IC 95 %, Sen, p de Mann–Kendall y
   de la prueba t, r₁, meses efectivos).
5. **Temperatura en tendencia:** lee la nota sobre la deriva orbital del satélite Terra
   ([sección 10](#10-limitaciones-conocidas)).
6. **Pestañas del modo Científico:** Series (compara con otra variable para ver la
   correlación), Metadatos (producto, DOI, procesamiento, advertencias) y Exportar (CSV).
7. **API directa:** <http://localhost:8000/docs> → `GET /api/trend-map/{variable}`.

Resultados de referencia con datos reales (2004 en adelante):

- **Temperatura de superficie (2004–2021):** sube en el 85 % de México; mediana +0.41 °C
  por década.
- **NO₂:** sube en el 74 % del país, pero en el centro de la Ciudad de México baja 22.8 % por
  década (Mann–Kendall p < 0.001).
- **Comparación con una referencia independiente (NASA Giovanni):** NO₂ por década en
  CDMX −12.5 % (referencia −13.8 %), Monterrey +6.4 % (+7.0 %) y Hermosillo +4.4 % (+3.8 %).

## 7. Pruebas

```bash
# Backend (en backend/, con el entorno activo)
pytest                                   # 100 pruebas
ruff check . && ruff format --check .    # estilo

# Frontend (en frontend/)
npm run typecheck                        # TypeScript estricto
npm run lint                             # ESLint
npm run test                             # 17 pruebas (Vitest)
```

Las pruebas usan el modo DEMO y límites de prueba, así que no necesitan los datos reales.
Incluyen la validación del mapa de tendencia contra el análisis completo de cada serie y
las respuestas en inglés.

## 8. Estructura del repositorio

```
trend-detectives/
├── backend/
│   ├── app/
│   │   ├── api/routes/          Rutas REST (capas, análisis, regiones, exportación)
│   │   ├── core/                Configuración, errores e idioma (i18n.py)
│   │   ├── schemas/models.py    Forma exacta de cada respuesta (Pydantic)
│   │   └── services/            Lógica: estadística (stats.py), tendencias
│   │                            (trend_monthly.py, trend_map.py, trend_service.py),
│   │                            datos DEMO y reales, imagen del mapa
│   ├── processing/              Descarga y procesamiento NASA (una carpeta por variable;
│   │                            fast/ = descarga rápida con Earth Engine y Harmony)
│   ├── tests/                   Pruebas pytest
│   └── pyproject.toml           Dependencias (núcleo, geo, processing, rapido, dev)
├── frontend/
│   └── src/
│       ├── pages/               Portada y área del Atlas
│       ├── components/          Mapa, leyendas, paneles, gráficas, controles
│       ├── i18n/                Textos en español e inglés (messages.ts)
│       ├── content/             Contenido educativo y glosario (es/en)
│       └── services/            Cliente de la API y tipos
├── metadata/
│   ├── sources/products.json    Fuente única de verdad de cada producto NASA
│   ├── sources/products.en.json Sus textos en inglés
│   └── documentation/           Auditoría de productos y métodos estadísticos
├── docs/                        Guías (instalación, ejecución, backend, NASA…)
├── data/                        Datos procesados (NO se sube a Git; ver sección 5)
├── .env.example                 Plantilla de configuración (copiar a .env)
└── PROJECT_STATUS.md            Qué está hecho, qué falta y qué está probado
```

## 9. Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| «No se pudo conectar con el servidor del Atlas» | La API no está corriendo, o falta Vite | Revisa que las dos terminales sigan abiertas (`uvicorn` y `npm run dev`) |
| El mapa no aparece o sale gris | Sin internet para el mapa base, o la página se quedó vieja | Revisa la conexión y recarga con `Ctrl + F5` |
| `ModuleNotFoundError: app` | No estás en `backend/` o el entorno no está activo | `cd backend` y activa `.venv` |
| PowerShell: «running scripts is disabled» | Política de ejecución de Windows | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `npm install` falla con «Unsupported engine» | Node.js antiguo | Instala Node 20.19+ o 22.12+ |
| «Address already in use» / puerto ocupado | Ya hay otra API o Vite abierto | Cierra la otra terminal o usa `--port 8001` (y ajusta `frontend/vite.config.ts`) |
| `MissingGeoLibraries` (503) en modo real | Falta el extra `geo` | `pip install -e ".[geo,dev]"` |
| `sin_procesar` o «no se ha procesado» | Falta ese mes en `data/` | Ver [sección 5](#5-usar-los-datos-reales-de-nasa) |
| «Los límites del INEGI todavía no están cargados» | No se descargaron los límites | `python -m processing.cli limites` y reinicia la API |

## 10. Limitaciones conocidas

- **Deriva orbital de Terra (temperatura).** Desde 2020 el satélite Terra no corrige su
  órbita y mide cada vez más temprano, cuando el suelo está más frío. Por eso 2022–2025 sale
  de 2 a 4 °C por debajo de lo normal. La tendencia mensual de temperatura usa
  **2004–2021** y lo explica en pantalla. La tendencia anual complementaria (Theil–Sen) sí
  incluye esos años: léela con cautela.
- **NO₂ satelital:** es la columna de aire troposférica, no la concentración que se respira a
  nivel de calle.
- **Resolución de 0.25° (≈ 25 km)** en tendencias y estadísticas: mezcla ciudades con sus
  alrededores, y en la vista de tendencia la costa se ve escalonada.
- **IMERG V07 termina en septiembre de 2025.** Cuando NASA publique V08 conviene reprocesar
  todo el registro.
- **Temperatura y evapotranspiración solo existen en tierra.** Las nubes dejan huecos, que se
  muestran rayados como «sin dato».

## 11. Más documentación, seguridad y créditos

**Guías**

1. [Instalación detallada](docs/01-instalacion.md)
2. [Ejecución](docs/02-ejecucion.md)
3. [Frontend](docs/03-frontend.md)
4. [Backend y API](docs/04-backend.md)
5. [Procesamiento NASA](docs/05-procesamiento-nasa.md)
6. [Agregar una variable nueva](docs/06-agregar-variables.md)
7. [Cuenta Earthdata y credenciales](docs/07-earthdata.md)
8. [VS Code: extensiones y configuración](docs/08-vscode.md)
9. [Descarga rápida con Earth Engine y Harmony](docs/09-descarga-rapida.md)
10. [Auditoría de productos](metadata/documentation/auditoria-productos.md)

**Seguridad**

- Las credenciales de NASA y Google solo las usan los scripts de `backend/processing`, leídas
  de `.env` o de `~/.netrc`. **Nunca** llegan al navegador.
- `.env` y `.netrc` están en `.gitignore`. Comparte solo `.env.example`.
- La API solo acepta `GET`, valida todos los parámetros y nunca envía archivos completos al
  navegador: entrega estadísticas, series, rejillas pequeñas o imágenes.

**Créditos de datos**

Cita cada producto con su DOI (están en `metadata/sources/products.json`). Límites estatales
y municipales: Marco Geoestadístico del INEGI. Mapa base: OpenFreeMap / OpenStreetMap.
