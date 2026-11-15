# 3. Frontend

React 19 + TypeScript estricto + Vite 7 + Tailwind CSS 4, con MapLibre GL para el mapa,
Plotly para las gráficas y Lucide para los íconos.

## Cómo está organizado

```
frontend/src/
├── main.tsx, App.tsx        Arranque y rutas: "/" bienvenida, "/atlas" plataforma
├── pages/
│   ├── WelcomePage.tsx      Pantalla de bienvenida (diseño aprobado)
│   └── AtlasPage.tsx        Plataforma: encabezado, mapa, línea de tiempo y panel
├── context/
│   ├── atlasState.ts        Estado compartido (reducer) + lectura/escritura en la URL
│   └── AtlasStateContext.tsx Proveedor de React que sincroniza el estado con la URL
├── config/variables.ts      Lee metadata/sources/products.json (única fuente de verdad)
├── services/
│   ├── api.ts               Cliente HTTP de la API, mensajes de error en español
│   └── types.ts             Tipos de las respuestas (espejo de los modelos Pydantic)
├── components/
│   ├── ui/                  Botón, insignia, pestañas, selector, interruptor, estados
│   ├── brand/               Logotipo y mosaico de la bienvenida
│   ├── navigation/          Cambio de modo, menú, selector de variable y de región
│   ├── temporal/            Controles de mes/año, reproducción y línea de tiempo
│   ├── maps/                Mapa MapLibre, leyenda, capas, lectura de punto
│   ├── charts/              Envoltorio de Plotly y serie de tiempo
│   ├── educational/         Panel del modo Explorador
│   ├── scientific/          Panel del modo Científico
│   └── layout/DemoBanner    Franja «Datos de demostración»
├── content/                 Textos educativos (cada dato con su fuente) y glosario
├── hooks/                   useApi (peticiones cancelables), useRoute, usePlayback…
├── lib/                     Fechas, formato de números, clasificación de colores
└── styles/globals.css       Tokens de diseño (@theme de Tailwind 4) y temas claro/oscuro
```

## Ideas clave

**Un solo estado para los dos modos.** `atlasState.ts` guarda modo, variable, fecha,
fecha de comparación, región, punto y capas visibles. El modo Explorador y el Científico
leen el mismo estado, por eso cambiar de modo no pierde la consulta. El estado se refleja
en la URL (`?modo=…&variable=…&fecha=…&region=…&punto=…`), así que una vista se puede
compartir copiando el enlace y los botones atrás/adelante del navegador funcionan.

**Acciones del estado**: `setMode`, `setVariable` (si la fecha no existe para la nueva
variable la ajusta al mes válido más cercano y muestra un aviso), `setDate`, `stepMonth`,
`toggleCompare`, `setCompareDate`, `setRegion`, `setPoint`, `toggleLayer`,
`dismissNotice`, `replace`.

**Metadatos compartidos.** Nombres, unidades, cortes de color, rampas y fechas de
disponibilidad vienen de `metadata/sources/products.json`, el mismo archivo que usa el
backend. Si se corrige una fecha en la auditoría, se corrige en todos lados.

**El navegador nunca descarga NetCDF.** El mapa recibe:
- en modo DEMO, una rejilla pequeña (130 × 76 valores) que se pinta como imagen;
- en modo REAL, una URL de teselas PNG de TiTiler generadas desde el COG.

**Colores por intervalos.** Cada variable tiene 8 cortes y 9 colores
(`lib/classify.ts`). Los mismos cortes se usan en la leyenda, el mapa y TiTiler, y los
píxeles sin dato se muestran rayados, nunca como cero.

**Estados de la interfaz.** Cada panel distingue cargando (esqueleto), error (mensaje y
qué hacer), sin datos para esa fecha y datos de demostración.

**Temas.** El Explorador usa tema claro. El Científico empieza en oscuro y se puede
cambiar; la elección se guarda en `localStorage` (`atlas-tema-cientifico`).

## Componentes de interfaz (shadcn/ui)

`components.json` está configurado para shadcn/ui. Los componentes de `components/ui`
siguen sus convenciones (`cva` para variantes, `cn` para combinar clases) pero están
escritos en el proyecto, sin dependencias de Radix, para mantener el paquete ligero.
Si necesitas uno nuevo puedes añadirlo con `npx shadcn@latest add <componente>`; revisa
que no duplique uno existente.

## Variables de entorno (`frontend/.env`)

| Variable | Uso |
|---|---|
| `VITE_API_URL` | URL de la API si no está detrás del mismo dominio. Vacía en desarrollo (usa el proxy de Vite). |
| `VITE_BASEMAP_STYLE` | Estilo del mapa base. Por defecto OpenFreeMap Positron, sin clave. |

Todo lo que empieza con `VITE_` termina dentro del JavaScript público. **Nunca pongas ahí
credenciales.**

## Pruebas

- `npm run typecheck` — TypeScript estricto (`strict`, `noUncheckedIndexedAccess`).
- `npm run lint` — ESLint 9 con reglas de React Hooks.
- `npm run test` — Vitest + Testing Library (`atlasState.test.ts`, `lib.test.ts`,
  `ModeSwitch.test.tsx`).
- `npm run e2e` — Playwright (`e2e/atlas.spec.ts`) en escritorio y teléfono. Necesita la
  API en modo DEMO en el puerto 8000.

## Cómo añadir una pantalla o panel

1. Lee el estado con `useAtlas()`; no crees un estado paralelo.
2. Pide datos con `useApi((signal) => api.xxx(..., signal), [dependencias])`; ya cancela
   peticiones viejas y expone el estado de carga, error y datos.
3. Usa los componentes de `components/ui` y los tokens de `globals.css`
   (`bg-panel`, `text-texto-suave`, `border-borde`…), no colores sueltos.
4. Contempla los cuatro estados: cargando, error, sin datos y demo.
