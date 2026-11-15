import { expect, test } from "@playwright/test";

test("de la bienvenida al modo Explorador y luego al Científico sin perder la consulta", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("ATLAS");
  await page.getByRole("button", { name: /Explorar el medio ambiente/ }).click();
  await expect(page).toHaveURL(/\/atlas\?modo=explorador/);
  await expect(page.getByText("Modo DEMOSTRACIÓN")).toBeVisible();

  await page.getByRole("button", { name: "Temperatura" }).click();
  await page.getByLabel("Año consultado").selectOption("2012");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("2012");

  await page.getByRole("button", { name: /Científico/ }).click();
  await expect(page).toHaveURL(/modo=cientifico/);
  await expect(page).toHaveURL(/variable=temperature/);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Temperatura superficial terrestre");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("2012");
  await expect(page.getByText("Promedio")).toBeVisible();
});

test("NO₂ no permite fechas anteriores a octubre de 2004", async ({ page }) => {
  await page.goto("/atlas?modo=explorador&variable=precipitation&fecha=2002-05");
  await page.getByRole("button", { name: "NO₂" }).click();
  await expect(page.getByRole("status").filter({ hasText: "octubre de 2004" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("octubre de 2004");
});
