# Datos

Esta carpeta no se sube a Git (solo su estructura). Todo se regenera con
`python -m processing.cli` desde `backend/`.

```
data/
├── raw/<variable>/              Descargas originales o recortes a México
├── processed/monthly/<variable>/ NetCDF mensual en resolución nativa (<variable>_AAAA-MM.nc)
├── processed/comparative/       Cubos 0.25° (<variable>_0p25.nc)
├── optimized/cog/<variable>/    Cloud Optimized GeoTIFF para el mapa (<variable>_AAAA-MM.tif)
├── optimized/zarr/              Cubos 0.25° en Zarr (opcional)
├── boundaries/                  inegi/ (shapefiles originales) y GeoJSON simplificados
└── catalog/catalog.json         Índice de todo lo procesado
```

Los píxeles nunca se guardan en una base de datos relacional: viven en estos archivos.
