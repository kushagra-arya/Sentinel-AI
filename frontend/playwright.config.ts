import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    ignoreHTTPSErrors: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    viewport: { width: 1440, height: 960 }
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
