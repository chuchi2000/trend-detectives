# 9. Descarga rápida (Earth Engine + Harmony)

Descarga 2004–2025 completo en **unas horas** en lugar de días. Los cálculos se hacen en
los servidores de Google y de NASA, y a tu computadora solo llega México.

| Variable | Dónde se calcula | Qué llega a tu computadora |
|---|---|---|
| Precipitación | Google Earth Engine (`NASA/GPM_L3/IMERG_MONTHLY_V07`) | Mes ya en mm/mes, malla nativa 0.1° |
| Evapotranspiración | Google Earth Engine (`MODIS/061/MOD16A2GF`) | Mes ya calculado, mapa a 0.025° |
| Temperatura | Google Earth Engine (`MODIS/061/MOD11A2`) | Mes ya calculado, mapa a 0.025° |
| NO₂ | NASA Harmony (recorte de OMNO2d V004) | Días recortados a México (~1 % del archivo mundial) |

Los resultados son los **mismos archivos** que el procesamiento clásico (NetCDF mensual,
COG y catálogo), con las **mismas reglas de calidad**. `comparativo`, la API y las
gráficas no cambian.

**Diferencia con el método clásico:** el mapa de evapotranspiración y temperatura se
guarda a 0.025° (≈ 2.8 km) en lugar de 500 m / 1 km. El cálculo mensual sí se hace
píxel a píxel en la resolución nativa y luego se promedia por área. Para el mapa
nacional y para la malla comparativa de 0.25° no hay diferencia práctica. Si necesitas
más detalle: `--resolucion-mapa 0.01` (≈ 1.1 km). Más lento.

## 1. Cuenta de Google Earth Engine (una sola vez)

1. Entra a <https://earthengine.google.com/> → **Get Started** con tu cuenta de Google.
2. Crea un **proyecto de Google Cloud** cuando te lo pida y elige **uso no comercial**
   (estudiante / investigación). Es gratis para ese uso.
3. Anota el **ID del proyecto** (algo como `atlas-ambiental-123456`).
4. Agrégalo a tu `.env` (carpeta principal):
   ```
   EE_PROJECT=atlas-ambiental-123456
   ```

## 2. Instalar (una sola vez)

En `backend/` con el entorno activo:

```
pip install -e ".[processing,rapido,dev]"
python -m processing.cli ee-login
```

`ee-login` abre el navegador para autorizar tu cuenta de Google. Al terminar debe decir
«Earth Engine listo».

Para el NO₂ (Harmony) se usan tu `EARTHDATA_USERNAME` y `EARTHDATA_PASSWORD` del `.env`.

## 3. Probar con un mes

```
python -m processing.cli rapido --inicio 2015-07 --fin 2015-07
python -m processing.cli catalogo
```

Las cuatro variables deben aparecer con `native` y `comparative`.

## 4. Todo el periodo

```
python -m processing.cli rapido --inicio 2004-01 --fin 2025-12
```

- Corre el NO₂ (Harmony) y las otras tres variables (Earth Engine) **al mismo tiempo**.
- Respeta la disponibilidad de cada producto (NO₂ desde 2004-10, precipitación hasta
  2025-09).
- Al final reconstruye la malla comparativa.
- **Si se corta, vuelve a ejecutar el mismo comando:** se salta lo ya hecho.
- Tiempo estimado: 2 a 3 horas, según tu internet y las filas de espera de Google y NASA.

Opciones útiles:

| Opción | Para qué |
|---|---|
| `--variables precipitacion temperatura` | Solo algunas variables |
| `--hilos 8` | Más meses a la vez en Earth Engine (por defecto 6) |
| `--resolucion-mapa 0.01` | Mapa de MODIS más detallado (más lento) |
| `--forzar` | Recalcular meses ya hechos en Earth Engine |

## Problemas comunes

| Mensaje | Solución |
|---|---|
| `Falta EE_PROJECT` | Agrega `EE_PROJECT=…` al `.env` |
| `Earth Engine API has not been used in project` | Abre el enlace del mensaje y pulsa **Enable** |
| `not registered to use Earth Engine` | Termina el registro no comercial del paso 1 |
| `Too many concurrent aggregations` | Normal: el script espera y reintenta. Si persiste, usa `--hilos 3` |
| NO₂: `No se encontraron latitudes/longitudes` | Envía el mensaje completo: indica el formato exacto que devolvió Harmony |

## Estado

Escrito y probado en su lógica (mallas, división en solicitudes, reglas de compuestos y
agrupación de días), pero **no se ha ejecutado aún contra Earth Engine ni Harmony**. La
prueba de un mes (paso 3) es la que lo confirma.
