# 8. VS Code: extensiones y configuración

Abre siempre la **carpeta raíz** del proyecto (`Mexico_Environmental_Atlas`), no
`frontend/` ni `backend/` por separado: la configuración de `.vscode/` asume la raíz.

Al abrirla, VS Code muestra «Este espacio de trabajo tiene extensiones recomendadas».
Pulsa **Instalar**. La lista está en `.vscode/extensions.json`; también la ves con
`Ctrl/Cmd+Shift+P` → «Extensions: Show Recommended Extensions».

## Extensiones

### Indispensables

| Extensión | ID | Para qué |
|---|---|---|
| ESLint | `dbaeumer.vscode-eslint` | Marca errores de TypeScript/React mientras escribes y los corrige al guardar |
| Prettier | `esbenp.prettier-vscode` | Formatea TS, JSON y CSS igual para todos |
| Tailwind CSS IntelliSense | `bradlc.vscode-tailwindcss` | Autocompleta clases y muestra el CSS que generan; reconoce los tokens del proyecto |
| Python | `ms-python.python` | Entorno virtual, ejecución, depuración y pruebas |
| Pylance | `ms-python.vscode-pylance` | Análisis de tipos y autocompletado de Python |
| Ruff | `charliermarsh.ruff` | Lint, formato y orden de imports de Python (sustituye a flake8, isort y black) |

### Opcionales

| Extensión | ID | Para qué |
|---|---|---|
| ES7+ React snippets | `dsznajder.es7-react-js-snippets` | Atajos para crear componentes (`rafce`…) |
| Jupyter | `ms-toolsai.jupyter` | Abrir los cuadernos de `notebooks/` |
| GitLens | `eamodio.gitlens` | Ver quién cambió cada línea y el historial |
| REST Client | `humao.rest-client` | Probar la API desde `backend/api.http` |
| Container Tools | `ms-azuretools.vscode-containers` | Ver y controlar los contenedores (TiTiler, PostGIS). Es la extensión que ahora usa Microsoft para Docker; la antigua «Docker» se convirtió en un paquete que la instala |

No hay extensión de TypeScript: viene integrada en VS Code. La configuración le indica
usar la versión del proyecto (`frontend/node_modules/typescript`), la misma de
`npm run typecheck`. La primera vez, abre un `.tsx` y acepta «Use Workspace Version», o
`Ctrl/Cmd+Shift+P` → «TypeScript: Select TypeScript Version».

## Qué hace `.vscode/settings.json`

| Ajuste | Efecto |
|---|---|
| `editor.formatOnSave` | Formatea al guardar: Prettier en TS/JSON/CSS, Ruff en Python |
| `source.fixAll.eslint` | Aplica las correcciones automáticas de ESLint al guardar |
| `source.organizeImports.ruff` | Ordena los imports de Python al guardar |
| `eslint.workingDirectories` | ESLint usa la configuración de `frontend/` |
| `typescript.tsdk` | Usa el TypeScript del proyecto (validación estricta idéntica a la del CLI) |
| `python.defaultInterpreterPath` | Usa `backend/.venv` |
| `python.analysis.typeCheckingMode: basic` | Pylance avisa de errores de tipos sin ser excesivo |
| `python.testing.*` | Las pruebas pytest aparecen en el panel de pruebas (ícono de matraz) |
| `tailwindCSS.experimental.classRegex` | Autocompletado de Tailwind dentro de `cn(…)` y `cva(…)` |
| `search.exclude` | La búsqueda ignora `node_modules`, `dist` y los datos pesados |

## Depurar

`.vscode/launch.json` trae dos configuraciones (panel «Ejecutar y depurar»):

- **API FastAPI (depurar)**: arranca Uvicorn con puntos de interrupción.
- **Procesamiento: precipitación de prueba (julio 2015)**: ejecuta el mes de prueba paso
  a paso. Útil para ver cómo cambian los arreglos en cada filtro.

Ambas leen tu `.env`.
