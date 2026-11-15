import { defineConfig, devices } from "@playwright/test";

/**
 * Pruebas de extremo a extremo: necesitan el backend en modo DEMO en el puerto
 * 8000 y levantan el frontend con Vite. Ver docs/03-frontend.md.
 */
export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://localhost:5173", trace: "on-first-retry" },
  webServer: { command: "npm run dev", url: "http://localhost:5173", reuseExistingServer: true },
  projects: [
    { name: "escritorio", use: { ...devices["Desktop Chrome"] } },
    { name: "telefono", use: { ...devices["Pixel 7"] } },
  ],
});
