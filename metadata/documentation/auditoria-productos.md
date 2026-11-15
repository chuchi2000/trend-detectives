# Auditoría de productos

**Fecha**: 14 de noviembre de 2026.
**Método**: consulta del catálogo CMR de NASA, páginas de producto de Earthdata, LP DAAC y
GES DISC, y especificaciones de archivo de LAADS. Los datos estructurados están en
[`../sources/products.json`](../sources/products.json); este documento explica las
decisiones.

> La disponibilidad aquí indicada es la que publica NASA. La disponibilidad **real** de
> cada mes se confirma al descargar y procesar, y queda en `data/catalog/catalog.json`.

## Resumen

| Variable | Producto | Versión | Resolución nativa | Paso | Disponible para el Atlas |
|---|---|---|---|---|---|
| Precipitación | GPM_3IMERGM | V07 | 0.1° | mensual | 2000-01 → 2025-09 |
| NO₂ troposférico | OMNO2d | V004 | 0.25° | diario | 2004-10 → 2025-12 |
| Evapotranspiración | MOD16A2GF | 061 | 500 m | 8 días | 2000-03 → 2025-12 |
| Temperatura superficial diurna | MOD11A2 | 061 | 1 km | 8 días | 2000-03 → 2025-12 |

**Periodo común de comparación: 2004-10 → 2025-09.**
**Malla comparativa: 0.25°**, EPSG:4326, −118.75 a −86.25 de longitud y 14.25 a 33.25 de
latitud (130 × 76 celdas).

## Hallazgos que cambian el plan original

1. **IMERG V07 Final termina en septiembre de 2025.** Sus productos de entrada pasaron a
   la versión 08 y V08 Final aún no está publicado. Octubre a diciembre de 2025 quedan sin
   precipitación. Cuando salga V08 Final conviene reprocesar todo el registro con V08 y
   no unir V07 con V08 en una misma serie.
2. **OMNO2d: se recomienda V004 en lugar de V003.** V003 (C1266136111-GES_DISC) dejó de
   actualizarse en 2019. V004 (C3333493715-GES_DISC, «Ver 5.0, Col 004») es la colección
   vigente. El código acepta ambas.
3. **NO₂ empieza en octubre de 2004**, no en 2000 (Aura se lanzó en julio de 2004).
4. **MODIS empieza en febrero de 2000.** Por la regla de cobertura mensual, el primer mes
   completo de ET y LST es **marzo de 2000**.
5. **MOD16A2GF tiene códigos especiales** (32761–32766: agua, urbano, desierto, nieve,
   sin clasificar…). No son ET cero y se eliminan.
6. **Deriva orbital de Terra.** Desde 2020 Terra no corrige su órbita y su hora de paso se
   adelanta. Afecta sobre todo a la LST diurna: los meses desde 2020 llevan la bandera
   `deriva_orbital_terra`.

## Decisiones por producto

### GPM_3IMERGM V07

- DOI 10.5067/GPM/IMERG/3B-MONTH/07 · C2723754851-GES_DISC · HDF5.
- `Grid/precipitation` (mm/h, relleno −9999.9). Es el campo calibrado con pluviómetros,
  el recomendado para la mayoría de usos.
- mm/mes = mm/h × 24 × días del mes.
- Capas de calidad conservadas: `randomError`, `precipitationQualityIndex`.
- Antes de junio de 2014 la entrada proviene de la era TRMM; los cambios de constelación
  pueden producir saltos en estudios largos.

### OMNO2d V004

- DOI 10.5067/AURA/OMI/DATA3407 · HDF-EOS5 · diario · 0.25°.
- `ColumnAmountNO2TropCloudScreened` (molec/cm², relleno −1.27 × 10³⁰). El productor ya
  aplicó: ángulo cenital solar 0–85°, fracción de nubes < 30 %, banderas de calidad de la
  columna y de anomalía de filas, reflectividad del terreno.
- Mensual: media de días válidos, mínimo 3 por celda (ajustable). Se guarda el conteo.
- Los negativos individuales se conservan (ruido de recuperación).
- Se muestra en 10¹⁵ molec/cm².

### MOD16A2GF V061

- DOI 10.5067/MODIS/MOD16A2GF.061 · C2565791021-LPCLOUD · 500 m · 8 días.
- `ET_500m` int16, escala 0.1 → mm por compuesto; relleno 32767; especiales 32761–32766.
- `ET_QC_500m`: bit 0 = 0 algoritmo principal, 1 otra calidad; bits 3-4 nubes; bits 5-7
  algoritmo. Al ser la versión con huecos rellenados, el QC no elimina píxeles por defecto;
  se reporta la fracción con bit 0 = 1. Opción estricta disponible.
- Mensual: reparto uniforme de cada compuesto entre sus días; suma de los días del mes;
  escalado a mes completo con ≥ 80 % de días cubiertos.
- La versión GF se publica al cerrar cada año.

### MOD11A2 V061

- DOI 10.5067/MODIS/MOD11A2.061 · C2269056084-LPCLOUD · 1 km · 8 días.
- `LST_Day_1km` uint16, escala 0.02 → K; relleno 0; rango válido 7500–65535.
- `QC_Day`: bits 0-1 calidad obligatoria; bits 6-7 error de LST. Se acepta 00, o 01 con
  error ≤ 2 K.
- Mensual: media ponderada por días; ≥ 50 % de días cubiertos.
- Es temperatura de la superficie a la hora de paso de Terra (mañana), no del aire.

## Por qué 0.25° y conservativo

- Es la resolución nativa del producto más grueso (OMI). Ir más fino obligaría a
  sobremuestrear OMI, inventando detalle.
- El promedio conservativo ponderado por área mantiene el total/promedio regional: la media
  de una región es la misma antes y después de re-mallar (salvo bordes).
- Se exige ≥ 50 % del área de cada celda con dato válido para no dejar que unos pocos
  píxeles representen una celda de ≈ 25 km.

## Fuentes

- CMR GPM_3IMERGM: <https://cmr.earthdata.nasa.gov/search/collections.json?short_name=GPM_3IMERGM>
- Earthdata GPM_3IMERGM V07: <https://www.earthdata.nasa.gov/data/catalog/ges-disc-gpm-3imergm-07>
- Transición a IMERG V08: <https://gpm.nasa.gov/data/news/imerg-v08-transition-schedule>
- CMR OMNO2d: <https://cmr.earthdata.nasa.gov/search/collections.json?short_name=OMNO2d>
- Earthdata OMNO2d V004: <https://www.earthdata.nasa.gov/data/catalog/ges-disc-omno2d-004>
- README OMNO2: <https://acdisc.gesdisc.eosdis.nasa.gov/data//Aura_OMI_Level3/OMNO2d.003/doc/README.OMNO2.pdf>
- Earthdata MOD16A2GF V061: <https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod16a2gf-061>
- LAADS MOD16A2GF C6.1: <https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD16A2GF_c61>
- Guía MOD16 V6.1: <https://lpdaac.usgs.gov/documents/931/MOD16_User_Guide_V61.pdf>
- Earthdata MOD11A2 V061: <https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod11a2-061>
- LAADS MOD11A2 C6.1: <https://ladsweb.modaps.eosdis.nasa.gov/filespec/MODIS/61/MOD11A2>
- Deriva orbital de Terra: <https://terra.nasa.gov/?p=190003>
