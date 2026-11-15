# 5. Procesamiento NASA

> ¿Quieres 2004–2025 en horas y no en días? Usa la [descarga rápida](09-descarga-rapida.md).

Esta guía explica cómo pasar de los archivos de NASA a mapas mensuales que la API pueda
servir. Los fundamentos de cada decisión están en
[`metadata/documentation/auditoria-productos.md`](../metadata/documentation/auditoria-productos.md).

## El flujo en una imagen

```
NASA (GES DISC / LP DAAC)
   │  earthaccess (IMERG, OMI)      AppEEARS (MODIS: recorte de México, GeoTIFF)
   ▼
data/raw/<variable>/                 archivos originales o recortes
   │  filtros de calidad, factores de escala, conversión de unidades, agregación mensual
   ▼
data/processed/monthly/<variable>/<variable>_AAAA-MM.nc     NetCDF mensual, resolución nativa
data/optimized/cog/<variable>/<variable>_AAAA-MM.tif        COG para el mapa (TiTiler)
   │  re-malla conservativa a 0.25° (nunca se aumenta la resolución)
   ▼
data/processed/comparative/<variable>_0p25.nc               cubo tiempo × lat × lon
data/optimized/zarr/<variable>_0p25.zarr                    (opcional, --zarr)
   │
   ▼
data/catalog/catalog.json            índice: qué mes, qué archivo, cobertura, calidad
```

Cada script registra lo que produce en el catálogo. La API solo lee lo que está en él.

## Antes de empezar

1. Instalación nivel C (`pip install -e ".[processing,dev]"`), ver [01-instalacion.md](01-instalacion.md).
2. Cuenta Earthdata configurada y aplicaciones autorizadas, ver [07-earthdata.md](07-earthdata.md).
3. Desde `backend/`, con el entorno activo:

```bash
python -m processing.cli verificar-login
```

Debe terminar con «Credenciales correctas.».

## Primer paso obligatorio: un mes de prueba

No descargues 25 años de golpe. Empieza con **julio de 2015** (dentro del periodo común de
las cuatro variables, temporada de lluvias, buena cobertura de MODIS en el norte):

```bash
python -m processing.cli precipitacion --inicio 2015-07 --fin 2015-07
python -m processing.cli catalogo
```

Comprueba:

- Que existan `data/processed/monthly/precipitation/precipitation_2015-07.nc` y
  `data/optimized/cog/precipitation/precipitation_2015-07.tif`.
- Que el registro muestre valores plausibles (julio en el sur de México: cientos de mm).
- Cuánto ocupó `data/raw/precipitation/`. Multiplica por el número de meses para saber
  cuánto disco necesitarás.

Luego repite con las otras tres variables para el mismo mes. MODIS (ET y LST) pasa por
AppEEARS: la solicitud se encola en los servidores de NASA y puede tardar de minutos a
horas; el script espera y descarga solo cuando está lista.

```bash
python -m processing.cli no2 --inicio 2015-07 --fin 2015-07
python -m processing.cli evapotranspiracion --inicio 2015-07 --fin 2015-07
python -m processing.cli temperatura --inicio 2015-07 --fin 2015-07
python -m processing.cli comparativo
```

Abre el COG en QGIS para revisarlo visualmente antes de seguir.

## Comandos

| Comando | Opciones | Qué hace |
|---|---|---|
| `verificar-login` | — | Prueba las credenciales sin descargar nada |
| `precipitacion` | `--inicio --fin` `--solo-descarga` / `--solo-proceso` | IMERG mensual |
| `no2` | además `--min-dias N` (3), `--conservar-globales` | OMI diario → mensual |
| `evapotranspiracion` | además `--qc-estricto` | MOD16A2GF 8 días → mensual |
| `temperatura` | — | MOD11A2 8 días → mensual |
| `comparativo` | `--variables …`, `--zarr` | Cubos 0.25° |
| `limites` | `--tolerancia 0.005`, `--tolerancia-municipios 0.002`, `--origen carpeta` | Descarga los límites del INEGI (servicio web) o los convierte desde shapefiles |
| `catalogo` | — | Lista lo procesado |

`--solo-descarga` y `--solo-proceso` permiten, por ejemplo, descargar de noche y procesar
después, o reprocesar con otro parámetro sin volver a descargar.

## Método por variable

### Precipitación — GPM IMERG Final Monthly V07 (GPM_3IMERGM)

- **Acceso**: `earthaccess` (GES DISC), archivos HDF5 globales mensuales; se recortan a
  México al procesar.
- **Variable**: `Grid/precipitation`, en **mm/h** (tasa media del mes).
- **Calidad**: se descartan el relleno (−9999.9) y los negativos. Se guardan
  `randomError` y `precipitationQualityIndex` como capas de calidad.
- **Conversión**: mm/mes = mm/h × 24 × días del mes.
- **Periodo**: 2000-01 a 2025-09. V07 Final termina en septiembre de 2025; octubre a
  diciembre de 2025 quedan sin dato. Cuando NASA publique V08 Final, reprocesa todo el
  registro con V08: no mezcles versiones en una serie.

### NO₂ — OMI/Aura OMNO2d V004

- **Acceso**: `earthaccess` (GES DISC), un archivo global diario. El script recorta cada
  día a México en `raw/no2/OMNO2d_…_mexico_AAAA-MM.nc` y borra los globales (salvo con
  `--conservar-globales`).
- **Variable**: `ColumnAmountNO2TropCloudScreened` (columna troposférica, molec/cm²).
  NASA ya aplicó en este producto los filtros de ángulo solar, fracción de nubes < 30 %,
  banderas de calidad y de fila (*row anomaly*).
- **Mensual**: media de los días válidos de cada celda; se exige un mínimo de días
  (`--min-dias`, 3 por defecto) y se guardan el número de días y la cobertura.
- Los valores negativos individuales **se conservan**: son ruido de la recuperación y
  quitarlos sesgaría el promedio hacia arriba.
- **Periodo**: desde 2004-10 (inicio de la misión Aura OMI).
- **Ojo**: es la columna de aire troposférica, no la concentración al nivel del suelo.

### Evapotranspiración — MODIS/Terra MOD16A2GF v061

- **Acceso**: AppEEARS, recorte de México en GeoTIFF geográfico, capas `ET_500m` y
  `ET_QC_500m`. Una solicitud por año.
- **Escala**: valor × 0.1 = mm acumulados en el compuesto.
- **Valores especiales**: 32767 relleno; 32761–32766 son agua, urbano, desierto,
  nieve, etc. Se eliminan; **no** son evapotranspiración cero.
- **Calidad**: GF ya rellenó por interpolación las entradas de mala calidad, así que por
  defecto no se descartan píxeles por `ET_QC`; se guarda la fracción afectada como
  indicador. Con `--qc-estricto` se descartan.
- **De 8 días a mes**: cada compuesto cubre 8 días (el último del año, 5 o 6). Se reparte
  uniformemente entre sus días y se suman los días que caen en el mes. Si falta algún
  día, se escala a mes completo solo si hay ≥ 80 % de días cubiertos; si no, el mes queda
  sin dato.
- **Periodo**: el primer mes con cobertura suficiente es 2000-03.

### Temperatura de superficie — MODIS/Terra MOD11A2 v061

- **Acceso**: AppEEARS, capas `LST_Day_1km` y `QC_Day`.
- **Escala**: valor × 0.02 = K; °C = K − 273.15. El 0 es relleno.
- **Calidad**: se aceptan calidad 00, o 01 con error de LST ≤ 2 K. Se descartan 10 y 11.
- **Mensual**: media de los compuestos ponderada por los días de cada compuesto que caen
  en el mes; mínimo 50 % de días cubiertos.
- **Advertencia**: Terra dejó de corregir su órbita en 2020 y su hora de paso se adelanta.
  Los meses desde 2020 llevan la bandera `deriva_orbital_terra`. Lee con cautela las
  tendencias que incluyan esos años.

## Nivel comparativo de 0.25°

Para comparar variables hace falta una malla común. Se eligió **0.25°** porque es la
resolución más gruesa de las cuatro (OMI). Así ningún producto se «inventa» detalle: los
más finos se agregan, ninguno se interpola hacia arriba.

- **Malla**: −118.75 a −86.25 de longitud, 14.25 a 33.25 de latitud (130 × 76 celdas).
- **Método**: promedio conservativo ponderado por área: cada celda de 0.25° es el promedio
  de los píxeles finos que la tocan, ponderados por la superficie que comparten. Una celda
  necesita ≥ 50 % de su área con dato válido.
- **Periodo común**: 2004-10 a 2025-09.
- El cubo guarda, junto al valor, la fracción válida de cada celda.

## Límites del INEGI

Los límites de estados y municipios hacen funcionar el selector de región, los contornos
del mapa y las estadísticas por estado o municipio.

### Forma recomendada: servicio web del INEGI (un comando)

Desde `backend/`, con el entorno activo y conexión a internet:

```bash
python -m processing.cli limites
```

No necesita librerías extra ni descargar archivos a mano. El comando:

1. Pide al servicio web del INEGI (`gaia.inegi.org.mx/wscatgeo/v2/geo/mgee` y `/mgem`)
   los 32 estados y los municipios de cada uno: 64 descargas, unos minutos. Las copias
   originales quedan en `data/boundaries/inegi_servicio/`; si se corta, al repetirlo
   solo descarga lo que falta.
2. Simplifica las líneas (Douglas–Peucker; 0.005° ≈ 500 m en estados, 0.002° ≈ 200 m
   en municipios) para que el mapa cargue rápido. Islas más pequeñas que eso se omiten en
   la versión simplificada. Es una capa de visualización: entre vecinos pueden quedar
   huecos o traslapes de ese orden.
3. Escribe `states.geojson`, `municipalities/<clave>.geojson` y `mexico.geojson`.

Después **reinicia la API** (`Ctrl + C` y vuelve a ejecutar `uvicorn …`).

El servicio entrega coordenadas en EPSG:6365, el marco oficial de México; su diferencia
con WGS 84 es menor a un metro, así que se usan tal cual. Si el INEGI cambiara el formato,
el comando se detiene con un mensaje claro en lugar de generar límites erróneos.

### Alternativa: shapefiles del Marco Geoestadístico

Útil sin conexión estable o si quieres una edición específica del Marco Geoestadístico.
Necesita geopandas (`pip install geopandas`).

1. Descarga el Marco Geoestadístico en <https://www.inegi.org.mx/temas/mg/>.
2. Copia `00ent.shp` y `00mun.shp` (con sus `.dbf`, `.shx`, `.prj`) en
   `data/boundaries/inegi/`.
3. `python -m processing.cli limites --origen ../data/boundaries/inegi`

## Descarga completa

Cuando el mes de prueba esté bien, avanza por años. Ejemplo para ET:

```bash
python -m processing.cli evapotranspiracion --inicio 2001-01 --fin 2001-12
```

Recomendaciones:

- Procesa un año, revisa el catálogo y el espacio en disco, y sigue.
- Si se corta una descarga, vuelve a ejecutar el mismo comando. NO₂ omite los meses cuyo
  recorte ya existe en `data/raw/no2/`, y MODIS omite los años que tienen el archivo
  `_descarga_completa.json` (se escribe solo cuando AppEEARS terminó y todo se bajó).
  Para IMERG, `earthaccess` no vuelve a bajar archivos que ya están en la carpeta.
  Para forzar una nueva descarga, borra el recorte o el archivo `_descarga_completa.json`.
- Cuando tengas el procesado, puedes borrar `data/raw/<variable>/` para liberar espacio;
  `--solo-proceso` ya no funcionará para esos meses sin volver a descargar.
- Al terminar, `python -m processing.cli comparativo` reconstruye los cubos.

## Lo que este procesamiento no hace

- No interpola en el tiempo ni rellena meses faltantes.
- No convierte la falta de dato en cero.
- No aumenta la resolución de ningún producto.
- No mezcla versiones de un producto.
