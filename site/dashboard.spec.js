// Checks for the private dashboard (#120): it's built from fixture data by the
// real scripts/my_metrics.py, then checked like the page: WCAG 2.2 AA with axe
// at phone and desktop width in light and dark, the Copy command button, and
// no requests to other sites. Run: cd site && npx playwright test
const { test, expect } = require("@playwright/test");
const { AxeBuilder } = require("@axe-core/playwright");
const { execFileSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const now = new Date().toISOString().replace(/\.\d+Z$/, "Z");
const home = fs.mkdtempSync(path.join(os.tmpdir(), "dashboard-"));
const rules = path.join(home, ".bk-charterline");
fs.mkdirSync(rules);
const write = (name, value) => fs.writeFileSync(path.join(rules, name), typeof value === "string" ? value : JSON.stringify(value));
write("hook-log.jsonl", [
  { ts: now, type: "block", law: 13, check: "commit-message" },
  { ts: now, type: "ask", law: 38, check: "tier4-unapproved", tool: "mcp__db__execute_sql" },
  { ts: now, type: "ask", law: 38, check: "tier3-first-use", tool: "mcp__mail__create_draft" },
].map((r) => JSON.stringify(r)).join("\n") + "\n");
write("ai-tools.json", { version: 1, tools: {
  "mcp:db": { tier: 4, owner: "alice", label: "Supabase" },
  "mcp:mail": { tier: 3, owner: "alice", label: "Gmail", overrides: { send_message: 4 } },
  "mcp:viz": { tier: 1, owner: "alice", label: "Inline visuals" },
} });
write("ai-inventory.json", { "mcp|session|db": {}, "mcp|session|chat": {} });
execFileSync("python3", [path.join(__dirname, "..", "scripts", "my_metrics.py"), "--local-only"], { env: { ...process.env, HOME: home } });
const PAGES = ["index.html", "tools.html"].map((p) => "file://" + path.join(rules, "dashboard", p));

for (const colorScheme of ["light", "dark"]) {
  for (const width of [390, 1280]) {
    test(`the dashboard has no axe violations at ${width}px in ${colorScheme}`, async ({ page }) => {
      const problems = [];
      page.on("pageerror", (e) => problems.push("error: " + e.message));
      page.on("request", (r) => !r.url().startsWith("file://") && problems.push("request: " + r.url()));
      await page.emulateMedia({ colorScheme, reducedMotion: "reduce" });
      await page.setViewportSize({ width, height: 900 });
      for (const url of PAGES) {
        await page.goto(url);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
        const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]).analyze();
        expect(violations.map((v) => `${path.basename(url)}: ${v.id} (${v.nodes.length})`)).toEqual([]);
      }
      expect(problems).toEqual([]);
    });
  }
}

test("the Copy command button says where to paste", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto(PAGES[0]);
  await page.getByRole("button", { name: "Copy command" }).click();
  await expect(page.locator("#cmd-status")).toHaveText("Copied. Paste it into Claude Code and press Enter.");
});
