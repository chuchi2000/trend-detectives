# 2. Ejecución

## Modo DEMO (desarrollo de la interfaz)

Dos terminales, desde la raíz del proyecto:

```bash
# Terminal 1 — API
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

```bash
# Terminal 2 — interfaz
cd frontend
npm run dev
```

- Interfaz: <http://localhost:5173>
- Documentación de la API (Swagger): <http://localhost:8000/docs>
- Estado: <http://localhost:8000/api/health> → debe decir `"mode": "demo"`.

Vite reenvía todo lo que empieza por `/api` al puerto 8000 (ver `vite.config.ts`), así
que en desarrollo no hay problemas de CORS.

## Estados y municipios (funciona también en modo DEMO)

Para usar el selector de región y ver los contornos en el mapa, descarga una vez los
límites del INEGI. En una terminal, dentro de `backend/` y con el entorno activo:

```bash
python -m processing.cli limites
```

Al terminar, reinicia la API. Detalle en [05-procesamiento-nasa.md](05-procesamiento-nasa.md#límites-del-inegi).

## Modo DATOS REALES

Requiere haber procesado al menos un mes (ver [05-procesamiento-nasa.md](05-procesamiento-nasa.md)).

1. En `.env`: `ATLAS_DATA_MODE=real`.
2. `docker compose up -d titiler` (sirve las teselas de los COG).
3. Reinicia `uvicorn`.
4. `http://localhost:8000/api/health` debe decir `"mode": "real"`, y
   `http://localhost:8000/api/variables` muestra en `availability.processed` los meses
   procesados de cada variable.

Qué funciona con qué archivos:

| Función | Necesita |
|---|---|
| Mapa de una variable y fecha | COG nativo de ese mes + TiTiler |
| Valor en un punto | COG nativo |
| Estadísticas, series, tendencia, correlación, comparación | Cubo comparativo 0.25° (`python -m processing.cli comparativo`) |
| Estadísticas por estado/municipio | Además, límites del INEGI (`python -m processing.cli limites`) |

Si falta algo, la API responde con un código y un mensaje que dicen exactamente qué
falta (`sin_procesar`, `fecha_sin_datos`, `limites_no_cargados`,
`faltan_librerias_geoespaciales`…).

## Comandos útiles

| Dónde | Comando | Qué hace |
|---|---|---|
| backend | `pytest` | Pruebas |
| backend | `ruff check . && ruff format --check .` | Lint y formato |
| backend | `python -m processing.cli catalogo` | Lista lo procesado |
| frontend | `npm run typecheck` | TypeScript estricto |
| frontend | `npm run lint` | ESLint |
| frontend | `npm run test` | Pruebas unitarias (Vitest) |
| frontend | `npx playwright install chromium && npm run e2e` | Pruebas de extremo a extremo (necesita la API en marcha) |
| frontend | `npm run build` | Versión de producción en `frontend/dist` |

## Producción (resumen)

- Compila el frontend (`npm run build`) y sírvelo como archivos estáticos.
- Ejecuta la API con `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`
  detrás de un proxy (Nginx, Caddy).
- Pon el dominio real en `ATLAS_CORS_ORIGINS` y define `VITE_API_URL` al compilar si la
  API vive en otro dominio.
- TiTiler debe ser accesible desde el navegador: `TITILER_URL` es la URL pública.
