import { expect, request, test } from "@playwright/test";

const apiBaseUrl = process.env.PLAYWRIGHT_API_BASE_URL ?? "http://localhost/api";

test("Section 15 unattended demo flow completes in order", async ({ page }) => {
  const api = await request.newContext({
    baseURL: apiBaseUrl,
    ignoreHTTPSErrors: true
  });

  const started = await api.post("/demo/replay/start", {
    data: { mode: "accelerated", speed_multiplier: 600 }
  });
  expect(started.ok()).toBeTruthy();
  const startStatus = await started.json();
  expect(startStatus.current_step).toBe(1);
  expect(startStatus.plant_id).toBeTruthy();

  const login = await api.post("/auth/login", {
    data: {
      email: startStatus.demo_user_email,
      password: startStatus.demo_user_password
    }
  });
  expect(login.ok()).toBeTruthy();
  const tokens = (await login.json()).tokens;

  await page.addInitScript((token: string) => {
    window.localStorage.setItem("sentinelai_access_token", token);
  }, tokens.access_token);

  await page.goto("/dashboard");
  await expect(page.getByLabel("Current plant risk")).toContainText("low");

  await expect.poll(async () => {
    const response = await api.get(`/dashboard/summary?plant_id=${startStatus.plant_id}`, {
      headers: { Authorization: `Bearer ${tokens.access_token}` }
    });
    return (await response.json()).current_risk_level;
  }).toBe("low");

  await api.post("/demo/replay/advance", { data: { step: 2 } });
  const step2 = await api.get("/demo/replay/status");
  expect((await step2.json()).current_step_name).toContain("Gas slowly increasing");

  await api.post("/demo/replay/advance", { data: { step: 3 } });
  const step3 = await api.get("/demo/replay/status");
  expect((await step3.json()).current_step_name).toContain("Maintenance begins");

  await api.post("/demo/replay/advance", { data: { step: 4 } });
  const step4 = await api.get("/demo/replay/status");
  expect((await step4.json()).current_step_name).toContain("Workers enter");

  const advanced = await api.post("/demo/replay/advance", { data: { step: 5 } });
  expect(advanced.ok()).toBeTruthy();
  const alertStatus = await advanced.json();
  expect(alertStatus.alert_id).toBeTruthy();
  expect(alertStatus.incident_id).toBeTruthy();

  await page.goto("/dashboard");
  await expect(page.getByLabel("Current plant risk")).toContainText("high");
  await expect(page.getByText("High compound gas risk")).toBeVisible();

  await api.post("/demo/replay/advance", { data: { step: 6 } });
  await page.goto("/map");
  await expect(page.getByText("High compound gas risk")).toBeVisible();

  await api.post("/demo/replay/advance", { data: { step: 7 } });
  await page.goto("/timeline");
  await expect(page.getByText("Maintenance")).toBeVisible();
  await expect(page.getByText("Worker present in affected area")).toBeVisible();
  await expect(page.getByText("High compound gas risk")).toBeVisible();

  await api.post("/demo/replay/advance", { data: { step: 8 } });
  await page.goto("/assistant");
  await page.getByRole("combobox").selectOption("recommendation");
  await page.getByPlaceholder("Ask using indexed safety documents").fill(
    "What should we do when gas rises during maintenance with workers nearby?"
  );
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("Grounded response")).toBeVisible();
  await expect(page.getByText("Demo Gas Maintenance Controls")).toBeVisible();

  await api.post("/demo/replay/advance", { data: { step: 9 } });
  await page.goto("/emergency");
  await expect(page.getByText("Move workers out of the affected zone immediately.")).toBeVisible();
  await expect(page.getByText("North muster exit A1")).toBeVisible();

  await api.post("/demo/replay/advance", { data: { step: 10 } });
  await page.goto("/incidents");
  await expect(page.getByText("Gas + Maintenance + Workers")).toBeVisible();
  const report = await api.get(`/incidents/${alertStatus.incident_id}/report.csv`, {
    headers: { Authorization: `Bearer ${tokens.access_token}` }
  });
  expect(report.ok()).toBeTruthy();
  expect((await report.json()).filename).toContain("incident-");

  const perf = await api.get(`/demo/performance/dashboard?plant_id=${startStatus.plant_id}`);
  expect(perf.ok()).toBeTruthy();
  expect((await perf.json()).passed).toBe(true);
});
