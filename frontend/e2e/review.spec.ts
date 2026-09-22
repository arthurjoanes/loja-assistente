import { expect, test } from "@playwright/test";

test("filtro não suportado não aparece como receita geral", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar" }).click();
  const response = page.waitForResponse((value) =>
    value.url().endsWith("/api/assistant/query"),
  );
  await page
    .getByLabel("Pergunta", { exact: true })
    .fill("Quanto vendi ontem somente em dinheiro?");
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  const received = await response;
  expect(received.headers()["x-request-id"]).toBeTruthy();
  expect(received.headers()["x-content-type-options"]).toBe("nosniff");
  const answer = await received.json();
  expect(answer.status).toBe("needs_clarification");
  expect(answer.result).toBeNull();
  expect(answer.plan).toBeNull();
  await expect(page.getByTestId("answer").last()).toContainText("pagamento");
  await expect(page.getByTestId("answer").last()).not.toContainText("R$");
});

for (const size of [
  { width: 1280, height: 720 },
  { width: 390, height: 844 },
]) {
  test(`atalhos de análise aparecem cedo em ${size.width}×${size.height}`, async ({
    page,
  }, info) => {
    await page.setViewportSize(size);
    await page.goto("/");
    await page.getByRole("button", { name: "Entrar" }).click();
    await expect(page.locator(".suggestions")).toBeVisible();
    const visible = await page
      .locator(".suggestions button")
      .evaluateAll((buttons) => {
        return buttons.filter((button) => {
          const rect = button.getBoundingClientRect();
          return rect.top >= 0 && rect.bottom <= innerHeight && rect.width > 0;
        }).length;
      });
    expect(visible).toBeGreaterThanOrEqual(size.width > 720 ? 6 : 4);
    const readability = await page.evaluate(() => {
      const measure = (selector: string) =>
        Array.from(document.querySelectorAll(selector)).map((element) => ({
          text: element.textContent?.trim().slice(0, 70),
          size: parseFloat(getComputedStyle(element).fontSize),
        }));
      return {
        controls: measure(
          ".filter-field label, .filter-field select, .suggestions button strong",
        ),
        inputs: measure(".composer textarea"),
        metadata: measure(
          ".filter-guidance, .composer-footnote, .reference-date",
        ),
      };
    });
    for (const item of readability.controls)
      expect(item.size, item.text).toBeGreaterThanOrEqual(14);
    for (const item of readability.inputs)
      expect(item.size).toBeGreaterThanOrEqual(16);
    for (const item of readability.metadata)
      expect(item.size, item.text).toBeGreaterThanOrEqual(12);
    await info.attach("readability", {
      body: JSON.stringify(readability, null, 2),
      contentType: "application/json",
    });
    await page.screenshot({
      path: process.env.SCREENSHOT_DIR
        ? `${process.env.SCREENSHOT_DIR}/welcome-${size.width}x${size.height}.png`
        : info.outputPath("welcome.png"),
    });
  });
}
