import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import type { Answer, Favorite, Session } from "../src/lib/contracts";
import { money } from "../src/lib/format";

async function navigation(page: Page, name: string) {
  const opener = page.getByRole("button", { name: "Abrir menu", exact: true });
  if (await opener.isVisible()) await opener.click();
  await page.getByRole("button", { name, exact: true }).click();
}
async function login(page: Page, account = /Gerente · Aurora Casa/) {
  await page.goto("/");
  await page.getByRole("radio", { name: account }).check();
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Análise de vendas", exact: true }),
  ).toBeVisible();
  await navigation(page, "Nova análise");
}
async function editor(page: Page) {
  if (!(await page.getByLabel("Pergunta", { exact: true }).isVisible()))
    await page
      .getByRole("button", { name: "Editar pergunta", exact: true })
      .click();
}
async function ask(page: Page, question: string): Promise<Answer> {
  await editor(page);
  await page.getByLabel("Pergunta", { exact: true }).fill(question);
  const response = page.waitForResponse(
    (reply) =>
      reply.url().endsWith("/api/assistant/query") &&
      reply.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Enviar pergunta", exact: true })
    .click();
  const reply = await response;
  expect(reply.status()).toBe(200);
  const answer: Answer = await reply.json();
  await expect(page.getByTestId("answer").last()).toContainText(question);
  await expect(page.getByLabel("Pergunta", { exact: true })).toBeEnabled();
  return answer;
}
async function session(page: Page): Promise<Session> {
  const reply = await page.request.get("/api/auth/me");
  expect(reply.status()).toBe(200);
  return reply.json();
}
async function post(page: Page, route: string, body: unknown) {
  const current = await session(page);
  return page.request.post("/api" + route, {
    data: body,
    headers: {
      Origin: new URL(page.url()).origin,
      "X-CSRF-Token": current.csrf_token,
    },
  });
}
async function save(page: Page, name: string): Promise<Favorite> {
  await page
    .getByRole("button", { name: "Salvar consulta favorita", exact: true })
    .click();
  await page.getByLabel("Nome da consulta favorita").fill(name);
  const response = page.waitForResponse(
    (reply) =>
      reply.url().endsWith("/api/favorites") &&
      reply.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Salvar favorito", exact: true })
    .click();
  const reply = await response;
  expect(reply.status()).toBe(200);
  await expect(
    page.getByRole("button", { name: "Salvar favorito", exact: true }),
  ).toHaveCount(0);
  return reply.json();
}
function favoriteCard(page: Page, name: string) {
  return page
    .getByTestId("favorite")
    .filter({ has: page.getByRole("heading", { name, exact: true }) });
}
async function removeFavorite(page: Page, favorite: Favorite) {
  const reply = await page.request.get(`/api/favorites/${favorite.id}`);
  if (!reply.ok()) return;
  const current: Favorite = await reply.json();
  expect(
    (
      await post(page, `/favorites/${favorite.id}/delete`, {
        revision: current.revision,
      })
    ).status(),
  ).toBe(204);
}

test("esclarecimento permanece acessível com a próxima consulta recolhida e restaura contexto", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await page.getByLabel("Loja", { exact: true }).selectOption("a001");
  await page.getByLabel("Período", { exact: true }).selectOption("question");
  const answer = await ask(page, "Receita da loja Centro");
  expect(answer.pending_clarification?.partial_plan.store_ids).toEqual([
    "a001",
  ]);
  expect(answer.pending_clarification?.partial_plan.metric).toBe("revenue");
  await page
    .getByRole("button", { name: "Recolher próxima consulta", exact: true })
    .click();
  const panel = page.locator(".clarification-panel");
  const radio = panel.getByRole("radio", { name: /^Ontem/i });
  await expect(radio).toBeVisible();
  await expect(
    panel.getByRole("button", { name: "Confirmar escolha", exact: true }),
  ).toBeVisible();
  await expect(
    panel.getByRole("button", { name: "Confirmar escolha", exact: true }),
  ).toBeDisabled();
  await radio.focus();
  await page.keyboard.press("Space");
  await expect(radio).toBeChecked();
  await expect(panel.getByLabel("Escopo a confirmar")).toContainText(
    "Receita líquida",
  );
  await expect(panel.getByLabel("Escopo a confirmar")).toContainText(
    "Centro (a001)",
  );
  await expect(panel.getByLabel("Escopo a confirmar")).toContainText(
    "16/08/2026 (incluído) até 17/08/2026 (excluído)",
  );
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  await info.attach("pending-axe", {
    body: JSON.stringify(accessibility),
    contentType: "application/json",
  });
  expect(accessibility.violations).toEqual([]);
  await page.reload();
  await expect(panel).toBeVisible();
  await expect(panel.getByLabel("Escopo a confirmar")).toContainText(
    "Centro (a001)",
  );
  await panel.getByRole("radio", { name: /^Ontem/i }).check();
  const response = page.waitForResponse((reply) =>
    reply
      .url()
      .endsWith(
        `/conversations/${answer.conversation_id}/clarification/respond`,
      ),
  );
  await panel
    .getByRole("button", { name: "Confirmar escolha", exact: true })
    .press("Enter");
  const reply = await response;
  expect(reply.status()).toBe(200);
  const resolved: Answer = await reply.json();
  expect(resolved.plan?.period).toEqual({
    start: "2026-08-16",
    end: "2026-08-17",
  });
  expect(resolved.result?.scope.map((store) => store.id)).toEqual(["a001"]);
  await expect(page.getByTestId("answer").last()).toContainText(
    money(resolved.result!.totals!.revenue_cents),
  );
  await expect(panel).toHaveCount(0);
  await expect(page.locator(".analysis-result-focus").last()).toBeFocused();
});

test("consulta sem confirmação preserva os filtros até a recuperação", async ({
  page,
}) => {
  await login(page, /Supervisor · Aurora Casa/);
  const original = await ask(page, "Quanto vendi ontem na loja Centro?");
  await editor(page);
  await page.getByLabel("Loja", { exact: true }).selectOption("a002");
  await page.getByLabel("Período", { exact: true }).selectOption("week");
  const question = "Mostre a evolução diária da receita";
  const calls: Record<string, unknown>[] = [];
  await page.route("**/api/assistant/query", async (route) => {
    calls.push(route.request().postDataJSON());
    if (calls.length === 1)
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Serviço indisponível para este ensaio. Tente novamente.",
        }),
      });
    else await route.continue();
  });
  await page.getByLabel("Pergunta", { exact: true }).fill(question);
  await page
    .getByRole("button", { name: "Enviar pergunta", exact: true })
    .click();
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "Não foi possível confirmar a execução" }),
  ).toBeVisible();
  await expect(page.getByLabel("Pergunta", { exact: true })).toHaveValue(
    question,
  );
  await expect(page.getByLabel("Loja", { exact: true })).toHaveValue("a002");
  await expect(page.getByLabel("Período", { exact: true })).toHaveValue("week");
  await expect(page.getByLabel("Pergunta", { exact: true })).toBeDisabled();
  await expect(page.getByLabel("Loja", { exact: true })).toBeDisabled();
  await expect(page.getByLabel("Período", { exact: true })).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Enviar pergunta", exact: true }),
  ).toBeDisabled();
  await expect(page.getByTestId("answer").last()).toContainText(
    money(original.result!.totals!.revenue_cents),
  );
  expect(calls).toHaveLength(1);
  const recovery = page.waitForResponse((reply) =>
    reply
      .url()
      .endsWith(`/api/assistant/requests/${calls[0].client_request_id}`),
  );
  const retry = page.waitForResponse(
    (reply) =>
      reply.url().endsWith("/api/assistant/query") &&
      reply.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Recarregar estado atual", exact: true })
    .press("Enter");
  expect((await recovery).status()).toBe(404);
  const reply = await retry;
  expect(reply.status()).toBe(200);
  const received: Answer = await reply.json();
  expect(received.result?.scope.map((store) => store.id)).toEqual(["a002"]);
  expect(received.plan?.period).toEqual({
    start: "2026-08-10",
    end: "2026-08-17",
  });
  expect(calls).toHaveLength(2);
  expect(calls[1]).toEqual(calls[0]);
  expect(received.conversation_id).toBe(original.conversation_id);
  await expect(page.getByTestId("answer").last()).toContainText(question);
  await expect(page.getByLabel("Pergunta", { exact: true })).toBeEnabled();
  await expect(
    page.getByText(
      "A mesma intenção foi enviada com segurança e sua resposta foi confirmada.",
    ),
  ).toBeVisible();
});

test("conflito de favorito conserva edição e recarrega sem substituir filtros e pergunta", async ({
  page,
}) => {
  await login(page, /Supervisor · Aurora Casa/);
  const original = await ask(page, "Quanto vendi ontem na loja Centro?");
  const favorite = await save(page, `Conferência ${original.id.slice(0, 8)}`);
  try {
    await editor(page);
    await page.getByLabel("Loja", { exact: true }).selectOption("a002");
    await page.getByLabel("Período", { exact: true }).selectOption("month");
    await page
      .getByLabel("Pergunta", { exact: true })
      .fill("Minha próxima pergunta preservada");
    await navigation(page, "Favoritos");
    await favoriteCard(page, favorite.name)
      .getByRole("button", { name: "Renomear", exact: true })
      .click();
    const name = page.getByLabel("Novo nome do favorito");
    await name.fill("Meu nome ainda não salvo");
    expect(
      (
        await post(page, `/favorites/${favorite.id}/rename`, {
          revision: favorite.revision,
          name: "Nome gravado em outra aba",
        })
      ).status(),
    ).toBe(200);
    const conflict = page.waitForResponse((reply) =>
      reply.url().endsWith(`/favorites/${favorite.id}/rename`),
    );
    await page
      .getByRole("button", { name: "Confirmar novo nome", exact: true })
      .click();
    expect((await conflict).status()).toBe(409);
    await expect(name).toHaveValue("Meu nome ainda não salvo");
    await expect(
      page.getByRole("button", { name: "Confirmar novo nome", exact: true }),
    ).toBeDisabled();
    await page
      .getByRole("button", { name: "Recarregar estado atual", exact: true })
      .click();
    await expect(favoriteCard(page, "Nome gravado em outra aba")).toBeVisible();
    await expect(name).toHaveValue("Meu nome ainda não salvo");
    await expect(
      page.getByRole("button", { name: "Confirmar novo nome", exact: true }),
    ).toBeEnabled();
    const renamed = page.waitForResponse(
      (reply) =>
        reply.url().endsWith(`/favorites/${favorite.id}/rename`) &&
        reply.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Confirmar novo nome", exact: true })
      .click();
    const renamedReply = await renamed;
    expect(renamedReply.request().postDataJSON()).toEqual({
      revision: favorite.revision + 1,
      name: "Meu nome ainda não salvo",
    });
    expect(renamedReply.status()).toBe(200);
    expect((await renamedReply.json()).name).toBe("Meu nome ainda não salvo");
    await expect(favoriteCard(page, "Meu nome ainda não salvo")).toBeVisible();
    await navigation(page, "Análises");
    await editor(page);
    await expect(page.getByLabel("Pergunta", { exact: true })).toHaveValue(
      "Minha próxima pergunta preservada",
    );
    await expect(page.getByLabel("Loja", { exact: true })).toHaveValue("a002");
    await expect(page.getByLabel("Período", { exact: true })).toHaveValue(
      "month",
    );
    await expect(page.getByTestId("answer").last()).toContainText(
      money(original.result!.totals!.revenue_cents),
    );
  } finally {
    await removeFavorite(page, favorite);
  }
});

test("favorito abre cálculo histórico sem execução e reexecuta o plano fixo mesmo após mudar filtros", async ({
  page,
}) => {
  await login(page, /Supervisor · Aurora Casa/);
  const original = await ask(
    page,
    "Mostre a evolução diária da receita nos últimos 7 dias da loja Centro",
  );
  const favorite = await save(page, `Receita fixa ${original.id.slice(0, 8)}`);
  try {
    await editor(page);
    await page.getByLabel("Loja", { exact: true }).selectOption("a002");
    await page.getByLabel("Período", { exact: true }).selectOption("month");
    const mutationRequests: string[] = [];
    page.on("request", (request) => {
      if (
        request.method() === "POST" &&
        (/\/assistant\/query$/.test(request.url()) ||
          /\/favorites\/[^/]+\/run$/.test(request.url()))
      )
        mutationRequests.push(request.url());
    });
    await navigation(page, "Favoritos");
    await favoriteCard(page, favorite.name)
      .getByRole("button", { name: "Abrir cálculo registrado", exact: true })
      .press("Enter");
    await expect(page.getByTestId("answer").last()).toContainText(
      original.question,
    );
    await expect(page.getByTestId("answer").last()).toContainText(
      money(original.result!.totals!.revenue_cents),
    );
    expect(mutationRequests).toEqual([]);
    await expect(page.locator(".analysis-result-focus").last()).toBeFocused();
    await editor(page);
    await page.getByLabel("Loja", { exact: true }).selectOption("a002");
    await page.getByLabel("Período", { exact: true }).selectOption("month");
    await navigation(page, "Favoritos");
    const response = page.waitForResponse((reply) =>
      reply.url().endsWith(`/favorites/${favorite.id}/run`),
    );
    await favoriteCard(page, favorite.name)
      .getByRole("button", { name: "Executar novamente", exact: true })
      .press("Enter");
    const reply = await response;
    expect(reply.status()).toBe(200);
    const rerun: Answer = await reply.json();
    expect(rerun.id).not.toBe(original.id);
    expect(rerun.request_id).not.toBe(original.request_id);
    expect(rerun.plan).toEqual(original.plan);
    expect(rerun.result?.totals).toEqual(original.result?.totals);
    expect(rerun.result?.scope.map((store) => store.id)).toEqual(["a001"]);
    await expect(page.locator(".analysis-result-focus").last()).toBeFocused();
    expect(mutationRequests).toHaveLength(1);
    expect(mutationRequests[0]).toContain(`/favorites/${favorite.id}/run`);
    expect(
      await (await page.request.get(`/api/answers/${original.id}`)).json(),
    ).toEqual(original);
  } finally {
    await removeFavorite(page, favorite);
  }
});

test("falha controlada ao carregar favoritos não declara lista vazia e permite recarga real", async ({
  page,
}, info) => {
  await login(page, /Gerente · Brisa Casa/);
  const initial = await page.request.get("/api/favorites");
  expect(initial.status()).toBe(200);
  expect(await initial.json()).toEqual([]);
  let requests = 0;
  await page.route("**/api/favorites", async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    requests += 1;
    if (requests === 1)
      return route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Falha controlada ao carregar favoritos.",
        }),
      });
    return route.continue();
  });
  await info.attach("network-fixture", {
    body: "Only the first GET /api/favorites returns a controlled 500. Retry uses the real authorized API and database; no successful domain result is mocked.",
    contentType: "text/plain",
  });
  await navigation(page, "Favoritos");
  const failure = page
    .getByRole("status")
    .filter({ hasText: "Falha controlada ao carregar favoritos" });
  await expect(failure).toBeVisible();
  await expect(
    page.getByText("Nenhuma consulta favorita disponível.", { exact: true }),
  ).toHaveCount(0);
  const reply = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/favorites") &&
      response.request().method() === "GET",
  );
  await page
    .getByRole("button", { name: "Recarregar favoritos", exact: true })
    .press("Enter");
  expect((await reply).status()).toBe(200);
  await expect(failure).toHaveCount(0);
  await expect(
    page.getByText("Nenhuma consulta favorita disponível.", { exact: true }),
  ).toBeVisible();
  expect(requests).toBe(2);
});

test("credencial recusada foca a senha e preserva a conta para correção", async ({
  page,
}) => {
  await page.goto("/");
  const account = page.getByRole("radio", { name: /Supervisor · Aurora Casa/ });
  const password = page.getByLabel("Senha", { exact: true });
  await account.check();
  await password.fill("SenhaIncorreta!2026");
  const denied = page.waitForResponse(
    (reply) =>
      reply.url().endsWith("/api/auth/login") &&
      reply.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  expect((await denied).status()).toBe(401);
  await expect(page.locator("#login-error")).toBeVisible();
  await expect(password).toBeFocused();
  await expect(password).toHaveValue("SenhaIncorreta!2026");
  await expect(password).toHaveAttribute("aria-invalid", "true");
  await expect(password).toHaveAttribute("aria-describedby", "login-error");
  await expect(account).toBeChecked();
  await password.fill("LojaDemo!2026");
  const accepted = page.waitForResponse(
    (reply) =>
      reply.url().endsWith("/api/auth/login") &&
      reply.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Entrar", exact: true })
    .press("Enter");
  expect((await accepted).status()).toBe(200);
  await expect(
    page.getByRole("heading", { name: "Análise de vendas", exact: true }),
  ).toBeVisible();
});
