# Formato de los datos

Este es el acuerdo entre **Datos**, **Análisis** y **App**. Todo vive en `data/processed/` y se regenera con dos comandos (ver el README).

```
data/giovanni/                    CSV originales descargados de Giovanni (no se editan)
data/processed/catalogo.json      variables y regiones disponibles
data/processed/<variable>/<region>.csv              serie mensual limpia (fecha, valor)
data/processed/<variable>/tendencias.json           resultados para el mapa
data/processed/<variable>/series/<region>.json      serie para la gráfica al dar clic
data/processed/resumen_tendencias.csv               todo en una tabla, para revisar a ojo
```

Variables: `temperatura` (°C), `lluvia` (mm/mes), `no2` (10¹⁵ moléculas/cm²).
Regiones: `puebla`, `cdmx`, `monterrey`, `merida`, `hermosillo`.

## 1. `<region>.csv`: la serie limpia

```
fecha,valor
2000-01,12.43
2000-02,14.45
```

`no2` trae además `dias_validos`: cuántos días con dato tuvo ese mes. Si fueron menos de 5, el valor queda vacío.

## 2. `tendencias.json`: lo que pinta el mapa

```json
{
  "variable": "temperatura",
  "nombre": "Temperatura del aire a 2 m",
  "fuente": "MERRA-2 (M2TMNXSLV v5.12.4)",
  "unidades": "°C",
  "periodo": { "inicio": "2000-01", "fin": "2025-12" },
  "zonas": [
    {
      "id": "puebla", "nombre": "Puebla", "lat": 19.04, "lon": -98.2,
      "pendiente_por_decada": 0.555, "ic95": [0.42, 0.69],
      "cambio_pct_por_decada": 3.38,
      "p_valor": 0.00003, "significativa": true, "direccion": "increasing",
      "promedio": 16.4, "meses": 312, "inicio": "2000-01", "fin": "2025-12"
    }
  ]
}
```

| Campo | Qué es |
|---|---|
| `pendiente_por_decada` | cuánto cambia la variable cada 10 años, en sus `unidades` |
| `ic95` | intervalo de confianza del 95 % de la pendiente |
| `cambio_pct_por_decada` | la pendiente como % del promedio (útil para lluvia y NO₂) |
| `p_valor` | de Mann-Kendall con corrección por autocorrelación (Hamed y Rao) |
| `significativa` | `true` si `p_valor < 0.05` |

## 3. `series/<region>.json`: la gráfica al dar clic

```json
{
  "id": "puebla",
  "fechas": ["2000-01", "2000-02", "..."],
  "valores": [12.43, 14.45, "..."],
  "anomalias": [-0.3, 0.1, "..."]
}
```

- `valores`: el dato mensual.
- `anomalias`: el mismo dato sin el ciclo de las estaciones (es lo que se usa para la tendencia).
- Un mes sin dato aparece como `null`.
