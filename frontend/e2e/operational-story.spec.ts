import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import type { Answer, Result } from "../src/lib/contracts";

async function ask(page: Page, question: string): Promise<Answer> {
  if (!(await page.getByLabel("Pergunta", { exact: true }).isVisible()))
    await page.getByRole("button", { name: "Editar pergunta" }).click();
  const waiting = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/assistant/query") &&
      response.request().method() === "POST",
  );
  await page.getByLabel("Pergunta", { exact: true }).fill(question);
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  const response = await waiting;
  expect(response.status()).toBe(200);
  const answer: Answer = await response.json();
  await expect(page.getByTestId("answer").last()).toContainText(question);
  return answer;
}

test("operational story: calculation, unsupported dimension and valid recovery", async ({
  page,
}, testInfo) => {
  const directory =
    process.env.STORY_OUTPUT_DIR || testInfo.outputPath("story");
  await mkdir(directory, { recursive: true });
  await page.goto("/");
  await page.getByRole("radio", { name: /Gerente · Aurora Casa/ }).check();
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(
    page.getByText("Demo sem IA", { exact: true }).last(),
  ).toBeVisible();
  const question = "Mostre a evolução diária da receita nos últimos 7 dias";
  const first = await ask(page, question);
  expect(first.status).toBe("ready");
  expect(first.result?.scope.map((store) => store.id)).toEqual(["a001"]);
  expect(first.result?.period).toEqual({
    start: "2026-08-10",
    end: "2026-08-17",
  });
  expect(first.result?.dataset_version).toBe("synthetic-v1");
  expect(first.result?.rows).toHaveLength(7);
  expect(
    first
      .result!.rows.reduce((sum, row) => sum + BigInt(row.revenue_cents), 0n)
      .toString(),
  ).toBe(first.result?.totals?.revenue_cents);
  const evidenceWaiting = page.waitForResponse((response) =>
    response.url().endsWith("/answers/" + first.id + "/evidence"),
  );
  await page.getByText("Cálculo", { exact: true }).click();
  const response = await evidenceWaiting;
  expect(response.status()).toBe(200);
  const evidence: Result = await response.json();
  expect(evidence).toEqual(first.result);
  await expect(page.getByText(first.request_id, { exact: true })).toBeVisible();
  await page.screenshot({
    path: path.join(directory, "01-calculation.png"),
    fullPage: true,
    animations: "disabled",
  });

  const refused = await ask(
    page,
    "Mostre a receita dos últimos 7 dias somente em dinheiro",
  );
  expect(refused.status).toBe("needs_clarification");
  expect(refused.plan).toBeNull();
  expect(refused.result).toBeNull();
  await page.screenshot({
    path: path.join(directory, "02-unsupported-dimension.png"),
    fullPage: true,
    animations: "disabled",
  });

  const recovered = await ask(page, question);
  expect(recovered.status).toBe("ready");
  expect(recovered.result?.scope).toEqual(first.result?.scope);
  expect(recovered.result?.period).toEqual(first.result?.period);
  expect(recovered.result?.rows).toEqual(first.result?.rows);
  expect(recovered.result?.totals).toEqual(first.result?.totals);
  await page
    .getByTestId("answer")
    .last()
    .getByRole("button", { name: "Tabela", exact: true })
    .click();
  await expect(
    page.getByText("Série por dia comercial", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(directory, "03-valid-recovery-table.png"),
    fullPage: true,
    animations: "disabled",
  });
  await writeFile(
    path.join(directory, "story.json"),
    JSON.stringify(
      {
        mode: "demo",
        dataset_version: "synthetic-v1",
        reference_date: "2026-08-17",
        capture_policy: {
          animations: "disabled",
          method:
            "Playwright screenshot fast-forwards finite CSS transitions; no image editing.",
          viewport: page.viewportSize(),
        },
        limits:
          "Synthetic fixture; no paid calls or human study. Row sum checks displayed result, not an independent source oracle.",
        first,
        evidence,
        refused,
        recovered,
        captured_at_utc: new Date().toISOString(),
      },
      null,
      2,
    ) + "\n",
  );
});
