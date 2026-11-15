# 6. Cómo incorporar un nuevo conjunto de datos

Ejemplo: agregar humedad del suelo, NDVI o aerosoles. El proyecto está pensado para que una
variable nueva toque pocos archivos y siga las mismas reglas científicas.

## 1. Auditar el producto antes de escribir código

Busca el producto en [NASA Earthdata Search](https://search.earthdata.nasa.gov/) o en
CMR (`https://cmr.earthdata.nasa.gov/search/collections.json?short_name=…`) y anota:

- Nombre corto, versión vigente, DOI, concept-id y centro de distribución (DAAC).
- Fechas reales de inicio y fin. **No supongas enero de 2000.**
- Resolución espacial y temporal (diaria, 8 días, 16 días, mensual).
- Capas: nombre, unidades, factor de escala, desplazamiento, relleno, rango válido.
- Capa de calidad y significado de cada bit (está en el manual de usuario del producto).
- Si existe una versión más nueva en preparación (para no mezclar versiones).
- Advertencias conocidas (deriva orbital, cambios de sensor, sesgos regionales).

Escribe todo en `metadata/documentation/auditoria-productos.md` con las fuentes.

## 2. Registrar la variable en `metadata/sources/products.json`

Copia el bloque de una variable parecida y edítalo. Campos obligatorios:

| Campo | Contenido |
|---|---|
| `name`, `short_label`, `unit`, `unit_long`, `data_type` | Textos que ve el usuario |
| `product` | `short_name`, `version`, `concept_id`, `doi`, `provider`, `access`… |
| `temporal` | `available_start`, `available_end` (AAAA-MM), resolución |
| `spatial` | Resolución nativa y si entra al nivel comparativo de 0.25° |
| `layers`, `special_values` | Lo que encontraste en la auditoría |
| `processing` | `monthly_method`, `conversion`, `quality_filter`, `comparative` |
| `display` | `scale`, `display_unit`, 8 `breaks`, 9 colores en `ramp`, `identity_color` |
| `caveats`, `sources` | Advertencias y enlaces |

La API y la interfaz leen este archivo: disponibilidad, unidades y colores aparecen solos.

## 3. Escribir el procesamiento

Crea `backend/processing/<variable>/pipeline.py` con dos funciones, `download(inicio, fin)`
y `process(inicio, fin)`. Reutiliza `processing/common`:

| Módulo | Para qué |
|---|---|
| `earthdata.py` | Iniciar sesión sin exponer credenciales |
| `appeears.py` | Recortes de productos de LP DAAC (MODIS, VIIRS…) |
| `modis.py` | Si es un compuesto MODIS de 8 o 16 días, define un `ModisSpec` y listo |
| `temporal.py` | Repartir compuestos entre meses, convertir tasas a totales |
| `qc.py` | Leer bits de calidad |
| `regrid.py` | Re-malla conservativa a 0.25° |
| `io.py` | Escribir NetCDF mensual y COG |

Reglas que el procesamiento debe cumplir:

1. Aplicar factor de escala y quitar relleno y códigos especiales **antes** de promediar.
2. Aplicar el filtro de calidad documentado.
3. Dejar sin dato (NaN) lo que no cumpla la cobertura mínima. Nunca cero.
4. Escribir el NetCDF mensual y el COG con los nombres
   `<variable>_AAAA-MM.nc` / `.tif`.
5. Registrar cada mes en el catálogo (`CatalogEntry`) con cobertura y banderas de calidad.

Añade el subcomando en `processing/cli.py` (diccionario `ALIASES` y la rama en
`_variable_command`).

## 4. Backend

- Añade el identificador al tipo `VariableId` en `app/api/deps.py`.
- Si quieres un atajo `/api/<variable>`, agrégalo en `app/api/routes/layers.py`.
- En modo demo, define cómo simularla en `app/services/demo_store.py` (un patrón espacial
  y un ciclo estacional plausibles). Recuerda que es demostración, no dato.

## 5. Frontend

- Añade el identificador al tipo `VariableId` y a la lista `VARIABLE_IDS` en
  `frontend/src/config/variables.ts`.
- Añade el ícono en `components/icons/VariableIcon.tsx`.
- Agrega datos curiosos (con fuente) en `content/educational.ts` y términos al glosario.

## 6. Pruebas y documentación

- Pruebas de conversión de unidades, filtro de calidad y agregación mensual en
  `backend/tests/test_processing.py`.
- Procesa **un mes de prueba**, revísalo en QGIS y compáralo con un valor publicado.
- Actualiza `PROJECT_STATUS.md` y la tabla de variables del `README.md`.
