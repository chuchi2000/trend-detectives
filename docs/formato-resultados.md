# Formato de resultados

Este es el acuerdo entre **Análisis** (quien escribe los archivos) y **App** (quien los lee). Mientras no haya datos reales, la app usa los ejemplos de `data/mock/`.

Por cada variable hay una carpeta en `data/processed/<variable>/` con dos tipos de archivo.

## 1. `tendencias.json`: lo que pinta el mapa

```json
{
  "variable": "T2M",
  "nombre": "Temperatura del aire a 2 m",
  "unidades": "°C",
  "fuente": "MERRA-2",
  "periodo": { "inicio": "1990-01", "fin": "2025-12" },
  "zonas": [
    {
      "id": "19.0_-98.0",
      "lat": 19.0,
      "lon": -98.0,
      "pendiente_por_decada": 0.31,
      "ic95": [0.18, 0.44],
      "p_valor": 0.002,
      "significativa": true
    }
  ]
}
```

| Campo | Qué es |
|---|---|
| `id` | `"<lat>_<lon>"` del centro de la celda; sirve para encontrar su serie |
| `pendiente_por_decada` | cuánto cambia la variable cada 10 años, en sus `unidades` |
| `ic95` | intervalo de confianza del 95 % de la pendiente |
| `p_valor` | de la prueba de Mann-Kendall |
| `significativa` | `true` si `p_valor < 0.05` |

## 2. `series/<id>.json`: la gráfica al dar clic

```json
{
  "id": "19.0_-98.0",
  "fechas": ["1990-01", "1990-02", "..."],
  "valores": [14.2, 15.1, "..."],
  "anomalias": [-0.3, 0.1, "..."]
}
```

- `valores`: el dato mensual original.
- `anomalias`: el mismo dato sin el ciclo de las estaciones (es lo que se usa para la tendencia).

Las series van en archivos separados para que el mapa cargue rápido.
