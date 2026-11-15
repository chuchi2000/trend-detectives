# 1. Instalación

Esta guía deja el proyecto listo en tu computadora. Hay tres niveles; instala solo lo que
vayas a usar.

| Nivel | Para qué | Qué instala |
|---|---|---|
| A. Interfaz + API demo | Ver y desarrollar la plataforma con datos simulados | Node, Python, dependencias núcleo |
| B. API con datos reales | Servir archivos NASA ya procesados | Nivel A + extra `geo` + Docker (TiTiler) |
| C. Procesamiento NASA | Descargar y procesar los productos | Nivel B + extra `processing` + cuenta Earthdata |

## Requisitos del sistema

- **Git**.
- **Python 3.11 o superior**. Comprueba con `python --version` (en Windows también `py --version`).
- **Node.js 20.19+ o 22.12+** (Vite 7 lo exige). Comprueba con `node --version`.
  Recomendado: instalar Node con [nvm](https://github.com/nvm-sh/nvm) o
  [nvm-windows](https://github.com/coreybutler/nvm-windows).
- **Docker Desktop** (solo niveles B y C, para TiTiler).
- **Espacio en disco**: el modo demo no necesita datos. Para datos reales, descarga primero
  un mes de prueba y mide cuánto ocupa antes de pedir años completos
  (ver [05-procesamiento-nasa.md](05-procesamiento-nasa.md)).

> **Windows**: la librería geoespacial (GDAL, que usan rasterio y geopandas) se instala
> sin problemas con las ruedas de `pip` en las versiones recientes. Si algo falla, usa
> [Miniforge](https://github.com/conda-forge/miniforge) y crea el entorno con conda-forge,
> o trabaja dentro de WSL2.

## Paso 1 — Copiar la configuración

Desde la raíz del proyecto:

```bash
cp .env.example .env               # Windows PowerShell: Copy-Item .env.example .env
cp frontend/.env.example frontend/.env
```

Por ahora no cambies nada: `ATLAS_DATA_MODE=demo`.

## Paso 2 — Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[dev]"            # Nivel A
# pip install -e ".[geo,dev]"      # Nivel B
# pip install -e ".[processing,dev]"  # Nivel C (incluye geo)
```

`-e` instala el paquete en modo editable: tus cambios en el código se usan sin reinstalar.

Comprueba:

```bash
pytest
```

Deben pasar todas las pruebas (las de la API se omiten si FastAPI no está instalado;
con `.[dev]` sí lo está).

## Paso 3 — Frontend

```bash
cd frontend
npm install
npm run typecheck
npm run test
```

## Paso 4 — VS Code (recomendado)

Abre la carpeta raíz del proyecto en VS Code. Te ofrecerá instalar las extensiones
recomendadas; acepta. Elige como intérprete de Python `backend/.venv`
(`Ctrl/Cmd+Shift+P` → «Python: Select Interpreter»). Detalle en
[08-vscode.md](08-vscode.md).

## Paso 5 — Solo niveles B y C

1. Instala y abre Docker Desktop.
2. `docker compose up -d titiler` desde la raíz.
3. Comprueba <http://localhost:8001/docs>.
4. Para el nivel C, configura tu cuenta Earthdata: [07-earthdata.md](07-earthdata.md).

## Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `npm install` falla con «Unsupported engine» | Node antiguo | Actualiza a 20.19+ o 22.12+ |
| `ModuleNotFoundError: app` | No estás en `backend/` o no activaste el entorno | `cd backend` y activa `.venv` |
| La interfaz dice «No se pudo conectar con la API» | El backend no está corriendo | Arranca `uvicorn` en el puerto 8000 |
| `MissingGeoLibraries` (503) en modo real | Falta el extra `geo` | `pip install -e ".[geo]"` |
