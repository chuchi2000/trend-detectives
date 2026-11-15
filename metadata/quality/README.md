# Calidad

Aquí se documentan los controles de calidad aplicados y los informes de cada lote
procesado.

## Controles aplicados (resumen)

| Variable | Filtro | Mínimo de cobertura mensual | Bandera |
|---|---|---|---|
| Precipitación | Relleno y negativos fuera | Producto ya mensual | — |
| NO₂ | Variable con filtro de nubes del productor; relleno fuera | 3 días válidos por celda | capa `n_valid_days` |
| Evapotranspiración | Relleno y códigos 32761–32766 fuera; QC informativo (estricto opcional) | 80 % de días | capa `other_quality_fraction` |
| Temperatura | QC 00, o 01 con error ≤ 2 K | 50 % de días | bandera `deriva_orbital_terra` (≥ 2020) |
| Malla 0.25° | Promedio conservativo | 50 % del área de la celda | capa `valid_fraction` |

Cada mes procesado guarda en `data/catalog/catalog.json` su número de píxeles válidos, su
cobertura y sus banderas, y la API las devuelve en `quality`.

**Ojo con la cobertura del catálogo**: hoy es la fracción de píxeles con dato dentro del
recuadro de México, que incluye mar y territorio de países vecinos. Para MODIS (que no mide
sobre el mar) saldrá baja aunque el territorio esté completo. Sirve para comparar meses de
una misma variable, no como «porcentaje del país». Calcularla solo sobre el territorio
nacional con la máscara del INEGI es una mejora pendiente (ver `PROJECT_STATUS.md`).

## Informes

Guarda aquí, por lote, una nota breve: fecha de proceso, rango, versión del producto,
meses con cobertura baja y cualquier anomalía observada al revisar los COG.
