import { expect, test, type Page } from "@playwright/test";
import type { Answer } from "../src/lib/contracts";

async function enter(page: Page, supervisor = false) {
  await page.goto("/");
  if (supervisor) await page.getByRole("radio", { name: /Supervisor/ }).check();
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(
    page.getByRole("heading", { name: "Análise de vendas" }),
  ).toBeVisible();
}
async function submit(page: Page, question: string): Promise<Answer> {
  await page.getByLabel("Pergunta", { exact: true }).fill(question);
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/assistant/query"),
  );
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  const received = await response;
  expect(received.status()).toBe(200);
  const answer: Answer = await received.json();
  await expect(page.getByTestId("answer").last()).toContainText(
    answer.question,
  );
  await expect(page.getByLabel("Pergunta", { exact: true })).toBeEnabled();
  return answer;
}

test("senha vazia, incorreta e limite preservam validação e recuperação", async ({
  page,
}) => {
  await page.goto("/");
  const password = page.getByLabel("Senha");
  let requests = 0;
  page.on("request", (r) => {
    if (r.url().endsWith("/api/auth/login")) requests += 1;
  });
  await password.fill("");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(password).toBeFocused();
  expect(
    await password.evaluate(
      (e) => (e as HTMLInputElement).validity.valueMissing,
    ),
  ).toBe(true);
  expect(requests).toBe(0);
  await password.fill("LojaDemo!2026 ");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.locator("#login-error")).toContainText(
    "E-mail ou senha inválidos",
  );
  await expect(password).toHaveAttribute("aria-invalid", "true");
  await expect(password).toHaveAttribute("aria-describedby", "login-error");
  await password.fill("x".repeat(201));
  await expect(password).toHaveValue("x".repeat(200));
  await password.fill("LojaDemo!2026");
  await password.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Análise de vendas" }),
  ).toBeVisible();
});

test("datas personalizadas mantêm edição real, bloqueiam inválidas e enviam recorte exato", async ({
  page,
}) => {
  await enter(page);
  await page.getByLabel("Período", { exact: true }).selectOption("custom");
  const start = page.getByLabel("Início (incluído)");
  const end = page.getByLabel("Fim (excluído)");
  const question = page.getByLabel("Pergunta", { exact: true });
  const send = page.getByRole("button", { name: "Enviar pergunta" });
  let queries = 0;
  page.on("request", (r) => {
    if (r.url().endsWith("/api/assistant/query")) queries += 1;
  });
  await question.fill("Qual foi a receita?");
  for (const [from, to] of [
    ["2026-08-18", "2026-08-17"],
    ["", "2026-08-17"],
    ["2026-08-17", "2026-08-17"],
    ["2026-05-18", "2026-08-17"],
  ]) {
    await start.fill(from);
    await end.fill(to);
    await question.focus();
    await expect(start).toHaveValue(from);
    await expect(start).toHaveAttribute("aria-invalid", "true");
    await expect(end).toHaveAttribute("aria-describedby", "period-error");
    await expect(page.locator("#period-error")).toContainText("1 a 90 dias");
    await expect(send).toBeDisabled();
    await question.press("Enter");
  }
  expect(queries).toBe(0);
  await start.fill("2026-05-19");
  await end.fill("2026-08-17");
  await expect(start).toHaveAttribute("aria-invalid", "false");
  await expect(send).toBeEnabled();
  const answer = await submit(page, "Qual foi a receita?");
  expect(answer.result?.period).toEqual({
    start: "2026-05-19",
    end: "2026-08-17",
  });
  expect(answer.result?.coverage.expected_days).toBe(90);
  await page.getByLabel("Período", { exact: true }).selectOption("custom");
  await start.fill("2026-08-15");
  await end.fill("2026-08-16");
  expect((await submit(page, "Qual foi a receita?")).result?.period).toEqual({
    start: "2026-08-15",
    end: "2026-08-16",
  });
});

test("lojas e períodos rápidos refletem seleção e datas explícitas prevalecem", async ({
  page,
}) => {
  await enter(page, true);
  const store = page.getByLabel("Loja", { exact: true });
  const preset = page.getByLabel("Período", { exact: true });
  for (const [selected, ids, period, start] of [
    ["a001", ["a001"], "yesterday", "2026-08-16"],
    ["a002", ["a002"], "week", "2026-08-10"],
    ["all", ["a001", "a002"], "month", "2026-07-18"],
  ] as const) {
    await store.selectOption(selected);
    await preset.selectOption(period);
    const answer = await submit(page, "Qual foi a receita?");
    expect(answer.result?.scope.map((s) => s.id)).toEqual(ids);
    expect(answer.result?.period).toEqual({ start, end: "2026-08-17" });
  }
  await preset.selectOption("week");
  expect((await submit(page, "Receita ontem")).result?.period.start).toBe(
    "2026-08-16",
  );
  await preset.selectOption("question");
  const unclear = await submit(page, "Receita");
  expect(unclear.status).toBe("needs_clarification");
  expect(unclear.result).toBeNull();
});

test("pergunta respeita espaços, acentos, quebra de linha, tamanho e múltiplas métricas", async ({
  page,
}) => {
  await enter(page);
  const input = page.getByLabel("Pergunta", { exact: true });
  await input.fill("   ");
  await expect(
    page.getByRole("button", { name: "Enviar pergunta" }),
  ).toBeDisabled();
  await input.fill("  RECEITA LÍQUIDA");
  await input.press("Shift+Enter");
  await input.pressSequentially("  ontem?  ");
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/api/assistant/query"),
  );
  await input.press("Enter");
  const ready: Answer = await (await response).json();
  expect(ready.status).toBe("ready");
  expect(ready.plan?.metric).toBe("revenue");
  await expect(input).toBeEnabled();
  await input.fill("x".repeat(1001));
  await expect(input).toHaveValue("x".repeat(1000));
  await expect(page.locator("#question-guidance")).toContainText("1000/1000");
  expect((await submit(page, "x".repeat(1000))).status).toBe(
    "needs_clarification",
  );
  const multiple = await submit(
    page,
    "Qual foi o ticket e a quantidade de pedidos ontem?",
  );
  expect(multiple.status).toBe("needs_clarification");
  await expect(page.getByTestId("answer").last()).not.toContainText("R$");
  await page.setViewportSize({ width: 320, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

for (const failure of ["network", "409", "503"]) {
  test(`falha ${failure} preserva pergunta, resultado anterior e permite tentar novamente`, async ({
    page,
  }) => {
    await enter(page);
    const first = await submit(page, "Receita ontem");
    let requests = 0;
    await page.route("**/api/assistant/query", async (route) => {
      requests += 1;
      if (failure === "network") await route.abort("failed");
      else
        await route.fulfill({
          status: Number(failure),
          contentType: "application/json",
          body: JSON.stringify({
            detail:
              failure === "409"
                ? "Conversa ocupada. Tente novamente."
                : "Serviço indisponível. Tente novamente.",
          }),
        });
    });
    const input = page.getByLabel("Pergunta", { exact: true });
    await input.fill("Pedidos ontem");
    await input.press("Enter");
    await expect(page.locator(".workspace-notice[role=alert]")).toBeVisible();
    await expect(input).toHaveValue("Pedidos ontem");
    await expect(input).toBeEnabled();
    await expect(page.getByTestId("answer")).toHaveCount(1);
    expect(requests).toBe(1);
    await page.unroute("**/api/assistant/query");
    const second = await submit(page, "Pedidos ontem");
    expect(second.conversation_id).toBe(first.conversation_id);
    expect(second.plan?.metric).toBe("orders");
  });
}

test("resposta lenta bloqueia envio duplicado e alterações de escopo", async ({
  page,
}) => {
  await enter(page);
  let release = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let requests = 0;
  await page.route("**/api/assistant/query", async (route) => {
    requests += 1;
    await held;
    await route.continue();
  });
  const input = page.getByLabel("Pergunta", { exact: true });
  await input.fill("Receita ontem");
  await input.press("Enter");
  await expect(input).toBeDisabled();
  await expect(page.getByLabel("Loja", { exact: true })).toBeDisabled();
  await expect(page.getByLabel("Período", { exact: true })).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Enviar pergunta" }),
  ).toBeDisabled();
  await page.keyboard.press("Enter");
  expect(requests).toBe(1);
  release();
  await expect(page.getByTestId("answer")).toHaveCount(1);
  await expect(input).toBeEnabled();
});

test("histórico, operação indisponível e nova análise mantêm contexto e foco", async ({
  page,
}) => {
  await enter(page);
  const answer = await submit(page, "Receita em 2026-08-15");
  const selected = page
    .getByRole("navigation", { name: "Histórico pessoal" })
    .locator('button[aria-current="page"]');
  await page.getByRole("button", { name: "Atendimentos" }).click();
  await expect(page.locator(".operation-stats")).toBeVisible();
  const total = await page
    .locator(".operation-stats strong")
    .first()
    .textContent();
  await page.route("**/api/operations", (route) => route.abort("failed"));
  await page.getByRole("button", { name: "Atualizar", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(
    "Exibindo a última consulta",
  );
  await expect(page.locator(".operation-stats strong").first()).toHaveText(
    total!,
  );
  await page.unroute("**/api/operations");
  await page.getByRole("button", { name: "Atualizar", exact: true }).click();
  await expect(page.getByText(/Exibindo a última consulta/)).toHaveCount(0);
  await page.getByRole("button", { name: "Nova análise" }).click();
  await expect(page.getByLabel("Pergunta", { exact: true })).toBeFocused();
  await expect(page.getByTestId("answer")).toHaveCount(0);
  await page
    .getByRole("navigation", { name: "Histórico pessoal" })
    .getByRole("button")
    .filter({ hasText: answer.question })
    .first()
    .click();
  await expect(selected).toContainText(answer.question);
  await expect(page.getByTestId("answer")).toHaveCount(1);
  await expect(page.getByLabel("Período", { exact: true })).toHaveValue(
    "effective",
  );
});

test("sessão expirada entre identificação e histórico volta ao login", async ({
  page,
}) => {
  await enter(page);
  await page.route("**/api/conversations", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: '{"detail":"Sessão expirada"}',
    }),
  );
  await page.reload();
  await expect(page.getByRole("heading", { name: "Entrar" })).toBeVisible();
  await expect(page.getByRole("status")).toContainText("Sessão expirada");
  await expect(
    page.getByRole("navigation", { name: "Histórico pessoal" }),
  ).toHaveCount(0);
});

test("proxy recusa JSON grande com contexto público consistente", async ({
  page,
}) => {
  const response = await page.request.post("/api/auth/login", {
    data: "x".repeat(16385),
    headers: { "Content-Type": "application/json" },
  });
  expect(response.status()).toBe(413);
  expect(response.headers()["x-content-type-options"]).toBe("nosniff");
  expect(response.headers()["cache-control"]).toBe("no-store");
  expect((await response.json()).request_id).toBe(
    response.headers()["x-request-id"],
  );
});

test("evidência com falha pode ser repetida sem perder o resultado", async ({
  page,
}) => {
  await enter(page);
  const answer = await submit(page, "Receita ontem");
  await page.route("**/api/answers/*/evidence", (route) =>
    route.abort("failed"),
  );
  const card = page.getByTestId("answer").last();
  await card.getByText("Cálculo", { exact: true }).click();
  await expect(card.getByRole("alert")).toContainText("Falha na conexão");
  await expect(
    card.getByRole("button", { name: "Tentar novamente" }),
  ).toBeVisible();
  await page.unroute("**/api/answers/*/evidence");
  await card.getByRole("button", { name: "Tentar novamente" }).click();
  await expect(card.locator(".request-id")).toContainText(answer.request_id);
  await expect(card.getByRole("alert")).toHaveCount(0);
});

test("erro tardio de evidência antiga não expira a nova identidade", async ({
  page,
}) => {
  await enter(page);
  await submit(page, "Receita ontem");
  let release = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let received = () => {};
  const started = new Promise<void>((resolve) => {
    received = resolve;
  });
  let delivered = () => {};
  const finished = new Promise<void>((resolve) => {
    delivered = resolve;
  });
  await page.route("**/api/answers/*/evidence", async (route) => {
    received();
    await held;
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: '{"detail":"Sessão antiga expirada"}',
    });
    delivered();
  });
  await page.getByText("Cálculo", { exact: true }).click();
  await started;
  await page.getByRole("button", { name: "Sair" }).click();
  await page.getByRole("radio", { name: /Gerente · Brisa Casa/ }).check();
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByLabel("Loja", { exact: true })).toHaveValue("b001");
  release();
  await finished;
  const answer = await submit(page, "Receita ontem");
  expect(answer.result?.scope.map((store) => store.id)).toEqual(["b001"]);
});

test("falha de conexão no login não acusa senha inválida", async ({ page }) => {
  await page.goto("/");
  await page.route("**/api/auth/login", (route) => route.abort("failed"));
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.locator("#login-error")).toContainText("Falha na conexão");
  await expect(page.getByLabel("Senha")).toHaveAttribute(
    "aria-invalid",
    "false",
  );
  await page.unroute("**/api/auth/login");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(
    page.getByRole("heading", { name: "Análise de vendas" }),
  ).toBeVisible();
});
