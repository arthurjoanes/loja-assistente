import { expect, test, type Page } from "@playwright/test";
import type { Answer } from "../src/lib/contracts";

async function ask(page: Page, question: string): Promise<Answer> {
  if (!(await page.getByLabel("Pergunta", { exact: true }).isVisible()))
    await page.getByRole("button", { name: "Editar pergunta" }).click();
  const response = page.waitForResponse((reply) =>
    reply.url().endsWith("/api/assistant/query"),
  );
  await page.getByLabel("Pergunta", { exact: true }).fill(question);
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  const answer: Answer = await (await response).json();
  await expect(page.getByTestId("answer").last()).toBeVisible();
  return answer;
}

test("rever um resultado preserva os dados e a continuação do último plano", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Análise de vendas" }),
  ).toBeVisible();
  const first = await ask(page, "Quanto vendi ontem?");
  const latest = await ask(
    page,
    "Mostre a evolução diária da receita nos últimos 7 dias",
  );
  await page.getByRole("button", { name: "Tabela", exact: true }).click();
  const selected = page.getByLabel("Resultado selecionado");
  let queries = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/api/assistant/query")) queries += 1;
  });
  await selected.focus();
  await selected.press("Home");
  await expect(selected).toHaveValue(first.id);
  await expect(selected).toBeFocused();
  await expect(page.getByTestId("answer").first()).toBeVisible();
  await expect(page.getByTestId("answer").last()).toBeHidden();
  await page.getByRole("link", { name: "Ir para o conteúdo" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
  await expect(selected).toHaveValue(first.id);
  await expect(
    page.getByText("Você está revendo um resultado anterior.", {
      exact: false,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Editar pergunta" }).click();
  await expect(page.getByLabel("Pergunta", { exact: true })).toBeFocused();
  await expect(selected).toHaveValue(first.id);
  expect(queries).toBe(0);
  await selected.selectOption(latest.id);
  await expect(
    page.getByText("Série por dia comercial", { exact: true }),
  ).toBeVisible();
  expect(queries).toBe(0);
  await selected.selectOption(first.id);
  const continued = await ask(page, "E nos sete dias anteriores?");
  expect(continued.result?.period).toEqual({
    start: "2026-08-03",
    end: "2026-08-10",
  });
  expect(continued.result?.intent).toBe("daily");
  await expect(selected).toHaveValue(continued.id);
  await expect(page.getByTestId("answer").first()).toBeHidden();
  await expect(page.getByTestId("answer").last()).toBeVisible();
  expect(queries).toBe(1);
  await page.getByRole("button", { name: "Nova análise" }).click();
  await expect(selected).toHaveCount(0);
  await expect(page.getByTestId("answer")).toHaveCount(0);
  await expect(page.getByLabel("Pergunta", { exact: true })).toBeFocused();
});
