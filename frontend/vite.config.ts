/// <reference types="vitest/config" />
import { fileURLToPath, URL } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Configuración de Vite:
// - React con recarga rápida y Tailwind CSS 4 como plugin.
// - "@" apunta a src/ y "@metadata" a la carpeta metadata/ de la raíz, para
//   que el frontend lea el mismo products.json que el backend.
// - En desarrollo, /api se redirige al backend FastAPI (puerto 8000), así no
//   hay problemas de CORS y el código usa rutas relativas.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@metadata": fileURLToPath(new URL("../metadata", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    fs: { allow: [".."] },
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: {
    chunkSizeWarningLimit: 4000,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: false,
    css: false,
    exclude: ["e2e/**", "node_modules/**"],
  },
});
