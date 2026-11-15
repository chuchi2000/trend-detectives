# Estado del proyecto

**Versión**: 0.1.0 · **Actualizado**: 14 de noviembre de 2026

Leyenda: ✅ hecho y probado · 🟡 hecho, sin probar con datos o servicios reales ·
⏳ pendiente

## Resumen

La plataforma completa funciona en **modo DEMO** (datos simulados, identificados como
tales). Todo el procesamiento NASA y el modo DATOS REALES están escritos y sus partes
numéricas tienen pruebas, pero **todavía no se ha descargado ningún archivo de NASA**: el
primer paso pendiente es el mes de prueba (julio de 2015) en tu computadora, con tu cuenta
Earthdata.

## Etapas

| # | Etapa | Estado | Notas |
|---|---|---|---|
| 1 | Diagnóstico y plan | ✅ | |
| 2 | Auditoría de productos | ✅ | `metadata/documentation/auditoria-productos.md` |
| 3 | Estructura, `.env.example`, `.gitignore`, VS Code | ✅ | |
| 4 | Metadatos compartidos (`products.json`) | ✅ | Usados por backend y frontend |
| 5 | Servicios del backend (fechas, malla, estadística, regiones, catálogo) | ✅ | Pruebas unitarias, salvo el catálogo (sin prueba propia) |
| 6 | API FastAPI | 🟡 | Lógica probada vía `AtlasService`; las rutas HTTP no se ejecutaron (ver abajo) |
| 7 | Modo DEMO | ✅ | |
| 8 | Utilidades de procesamiento (QC, escala, compuestos→mes, re-malla) | ✅ | Pruebas unitarias |
| 9 | Pipelines por variable (descarga + proceso) | 🟡 | Sin ejecutar contra NASA |
| 10 | Nivel comparativo 0.25° | 🟡 | Re-malla probada; el pipeline completo no |
| 10b | Descarga rápida (Earth Engine + Harmony) | 🟡 | Lógica probada (mallas, solicitudes, compuestos, agrupación); falta la primera ejecución real |
| 11 | Límites INEGI | 🟡 | Descarga desde el servicio web del INEGI con un comando: probada con respuestas simuladas en su formato; falta la ejecución real. Método con shapefiles sin probar |
| 12 | Frontend: bienvenida, mapa, modos, línea de tiempo | ✅ | Verificado en navegador (ver abajo) |
| 13 | Funciones avanzadas | ✅ en demo | Comparación, tendencia, correlación, estadísticas por región, CSV, PNG del mapa, animación, consulta por coordenada |
| 14 | Modo DATOS REALES de punta a punta | ⏳ | Requiere datos procesados y TiTiler |
| 15 | Documentación | ✅ | `README.md`, `docs/01…08` |
| 16 | Despliegue | ⏳ | |

## Qué se probó y cómo

Este proyecto se construyó en un entorno sin acceso a internet para instalar paquetes ni
descargar de NASA. Por eso:

**Probado**

- `pytest` en `backend/`: **76 pruebas pasan**. Cubren conversión de unidades, filtros QC
  por bits, reparto de compuestos de 8 días entre meses, mínimos de cobertura, re-malla
  conservativa (conserva el promedio), estadísticas ponderadas, Theil–Sen, Mann–Kendall,
  Pearson sobre anomalías, disponibilidad por producto, máscaras de estados y municipios,
  el servicio completo en modo demo (capas, punto, estadísticas, series, correlación,
  comparación, CSV), la reanudación de descargas MODIS y la preparación de límites desde el servicio
  del INEGI (simplificación, archivos de salida, reanudación, rechazo de formatos inesperados). El `FileStore` del modo real
  (lectura de COG y cubos con rasterio/xarray) **no tiene pruebas todavía**.
- `ruff check` y `ruff format`: sin observaciones.
- Interfaz: se compiló el código real de `frontend/src` con esbuild y Tailwind, y se probó
  en Chromium con Playwright contra una API de prueba que usa el mismo `AtlasService` en
  modo demo: **27 de 27 comprobaciones** (bienvenida, cambio de modo sin perder la
  consulta, URL compartible, meses sin datos desactivados, regiones, glosario, teclado,
  teléfono sin desbordamiento, sin errores de consola, franja de demo…).
- TypeScript estricto sobre los módulos sin React (estado, API, fechas, formato,
  clasificación, contenidos): sin errores.

**No probado todavía (pruébalo tú con los comandos de `docs/02-ejecucion.md`)**

- Las rutas FastAPI reales (`pytest` lo hará cuando instales `.[dev]`; `test_api.py` se
  omitió aquí por no tener FastAPI).
- `npm install`, `npm run typecheck` completo (componentes React), `npm run lint`,
  `npm run test` (Vitest) y `npm run e2e`. En la verificación, MapLibre, Plotly y Lucide se
  sustituyeron por versiones simuladas: el mapa real, las gráficas reales y los íconos
  reales no se han visto funcionando.
- Cualquier descarga: `earthaccess`, AppEEARS, lectura de HDF5/HDF-EOS de NASA, escritura
  de COG con rasterio, TiTiler, conversión de shapefiles del INEGI con geopandas y la descarga real del servicio web del INEGI.

## Decisiones técnicas

| Decisión | Motivo |
|---|---|
| OMNO2d **V004** en vez de V003 | V004 es la colección vigente; V003 dejó de actualizarse en 2019. El código acepta ambas |
| Precipitación hasta **2025-09** | IMERG V07 Final termina ahí; no se mezcla con V08 |
| Malla común de **0.25°**, promedio conservativo | Resolución del producto más grueso; nunca se sobremuestrea |
| MODIS vía **AppEEARS** | Recorta México y entrega GeoTIFF geográfico; evita descargar y mosaicar 20+ teselas sinusoidales por fecha |
| Catálogo en **JSON** y límites en **GeoJSON**; PostGIS diferido | Suficiente para 4 variables × ~310 meses; menos piezas que mantener al empezar. `docker-compose.yml` ya trae PostGIS para cuando haga falta |
| QC de MOD16A2GF informativo por defecto | El producto GF ya rellenó las entradas de mala calidad; descartar por bit 0 dejaría huecos que el producto resolvió. Modo estricto disponible |
| Negativos de NO₂ conservados | Quitarlos sesga hacia arriba el promedio |
| Correlación sobre anomalías, con tamaño de muestra efectivo e IC 95 % | Evita correlaciones espurias por el ciclo estacional y valores p optimistas |
| Tendencia: Mann–Kendall corregido por autocorrelación + IC 95 % de la pendiente de Sen | Separa tendencias sólidas de la variabilidad natural; validado con simulaciones (`metadata/documentation/metodos-estadisticos.md`) |
| Componentes UI propios con convenciones shadcn | Sin dependencias de Radix; mismo patrón `cva` + `cn` |
| Mapa real generado por la API (`ATLAS_MAP_MODE=imagen`) | Elimina la dependencia de Docker/TiTiler en Windows; filas ajustadas a Mercator (sin esto el centro se desplaza decenas de km). TiTiler sigue disponible como opción |

## Pendientes

1. **Mes de prueba real** (julio 2015) de las cuatro variables, en tu computadora.
2. Instalar dependencias y correr `pytest`, `npm run typecheck`, `npm run lint`,
   `npm run test`, `npm run e2e`; corregir lo que aparezca.
3. Ejecutar `python -m processing.cli limites` (descarga los límites del INEGI).
4. Levantar TiTiler y probar el modo real de punta a punta.
5. Calcular la cobertura del catálogo solo sobre el territorio nacional (hoy es sobre el
   recuadro, ver `metadata/quality/README.md`).
6. Descarga completa por años, revisando disco y calidad en cada lote.
7. Reprocesar precipitación cuando se publique IMERG V08 Final.
8. Migración a PostGIS si se requieren consultas espaciales más complejas.
9. Despliegue.

## Errores conocidos

Ninguno abierto en lo probado. Corregidos durante la construcción: índices de compuestos
en las pruebas, semillas no deterministas del modo demo (`hash()` → `crc32`), avisos de
`nanmean` en celdas vacías, propiedades de Plotly 3 obsoletas (`titlefont`, `locale`),
capas del mapa perdidas al cambiar de estilo, y alto del mapa en teléfono.
