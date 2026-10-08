// Checks for the BK Charterline page (#177): WCAG 2.2 AA with axe at phone and
// desktop width in light and dark, the tabs by keyboard, the real numbers,
// the page without JavaScript, and no requests to other sites.
// Run: cd site && npx playwright test
const { test, expect } = require("@playwright/test");
const { AxeBuilder } = require("@axe-core/playwright");
const path = require("path");

const PAGE = "file://" + path.join(__dirname, "index.html");
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

function watch(page) {
  const problems = [];
  page.on("pageerror", (e) => problems.push("error: " + e.message));
  page.on("console", (m) => m.type() === "error" && problems.push("console: " + m.text()));
  page.on("request", (r) => !r.url().startsWith("file://") && problems.push("request: " + r.url()));
  return problems;
}

for (const colorScheme of ["light", "dark"]) {
  for (const width of [320, 390, 1280]) {
    test(`no axe violations at ${width}px in ${colorScheme}`, async ({ page }) => {
      const problems = watch(page);
      await page.emulateMedia({ colorScheme, reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 900 });
      await page.goto(PAGE);
      for (const name of ["Product analytics", "Usage", "Governance"]) {
        await page.getByRole("tab", { name }).click();
      }
      // Before axe runs: axe re-reads the stylesheets over XHR, which a
      // browser blocks on file://, and that would show up as console errors.
      expect(problems).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      for (const name of ["Governance", "Product analytics", "Usage"]) {
        await page.getByRole("tab", { name }).click();
        const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze();
        expect(violations.map((v) => `${name}: ${v.id} (${v.nodes.length})`)).toEqual([]);
      }
    });
  }
}

test("the tabs work with the keyboard", async ({ page }) => {
  await page.goto(PAGE);
  await page.getByRole("tab", { name: "Governance" }).focus();
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("tab", { name: "Product analytics" })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator("#panel-product")).toBeVisible();
  await expect(page.locator("#panel-governance")).toBeHidden();
  await page.keyboard.press("End");
  await expect(page.getByRole("tab", { name: "Usage" })).toBeFocused();
  await page.keyboard.press("Home");
  await expect(page.getByRole("tab", { name: "Governance" })).toHaveAttribute("aria-selected", "true");
});

test("every real number matches data.js and shows its date", async ({ page }) => {
  await page.goto(PAGE);
  const { shown, data } = await page.evaluate(() => ({
    shown: [...document.querySelectorAll("[data-metric]")].map((el) => [el.dataset.metric, el.textContent]),
    data: window.DF_METRICS.numbers,
  }));
  expect(shown.length).toBeGreaterThan(5);
  for (const [name, text] of shown) {
    expect(Number(text.replace(/[^0-9]/g, "")), name).toBe(data[name].value);
    await expect(page.locator(`time[data-metric-date="${name}"]`).first()).toHaveAttribute("datetime", data[name].as_of);
  }
});

test.describe("without JavaScript", () => {
  test.use({ javaScriptEnabled: false });
  test("every demo panel shows, with its data table", async ({ page }) => {
    await page.goto(PAGE);
    for (const id of ["#panel-governance", "#panel-product", "#panel-usage"]) {
      await expect(page.locator(id)).toBeVisible();
      await expect(page.locator(`${id} table`).first()).toBeVisible();
    }
    await expect(page.locator(".tabs")).toBeHidden();
    await expect(page.locator(".theme")).toBeHidden();
  });
});
