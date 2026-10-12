import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type TestInfo } from "@playwright/test";
import type {
  Answer,
  Favorite,
  PendingClarification,
  Session,
} from "../src/lib/contracts";
import { money } from "../src/lib/format";

function screenshotPath(info: TestInfo, name: string) {
  return process.env.SCREENSHOT_DIR
    ? `${process.env.SCREENSHOT_DIR}/${name}`
    : info.outputPath(name);
}
async function login(page: Page, account = /Gerente · Aurora Casa/) {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Entrar", exact: true }),
  ).toBeVisible();
  await page.getByRole("radio", { name: account }).check();
  const response = page.waitForResponse(
    (reply) =>
      reply.url().endsWith("/api/auth/login") &&
      reply.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect(
    page.getByRole("heading", { name: "Análise de vendas", exact: true }),
  ).toBeVisible();
  await navigation(page, "Nova análise");
}
async function navigation(page: Page, name: string) {
  const trigger = page.getByRole("button", { name: "Abrir menu", exact: true });
  if (await trigger.isVisible()) await trigger.click();
  await page.getByRole("button", { name, exact: true }).click();
}
async function ask(page: Page, question: string): Promise<Answer> {
  if (!(await page.getByLabel("Pergunta", { exact: true }).isVisible()))
    await page.getByRole("button", { name: "Editar pergunta" }).click();
  await page.getByLabel("Pergunta", { exact: true }).fill(question);
  const response = page.waitForResponse(
    (reply) =>
      reply.url().endsWith("/api/assistant/query") &&
      reply.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
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
async function post(page: Page, path: string, body: unknown, csrf?: string) {
  return page.request.post("/api" + path, {
    data: body,
    headers: {
      Origin: new URL(page.url()).origin,
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
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
  const current = await page.request.get(`/api/favorites/${favorite.id}`);
  if (current.ok()) {
    const value: Favorite = await current.json();
    const currentSession = await session(page);
    const deleted = await post(
      page,
      `/favorites/${value.id}/delete`,
      { revision: value.revision },
      currentSession.csrf_token,
    );
    expect(deleted.status()).toBe(204);
  }
}

test("favoritos têm ações reais, nomes escapados, escopo fixo e cálculo histórico separado", async ({
  page,
}, info) => {
  await login(page);
  const original = await ask(page, "Quanto vendi ontem?");
  const name = `<img src=x onerror=alert(1)> ${original.id.slice(0, 8)}`;
  const saved = await save(page, name);
  try {
    const currentSession = await session(page);
    const duplicate = await post(
      page,
      "/favorites",
      { answer_id: original.id, name: "Outra tentativa" },
      currentSession.csrf_token,
    );
    expect(duplicate.status()).toBe(200);
    expect((await duplicate.json()).id).toBe(saved.id);
    await navigation(page, "Favoritos");
    const card = favoriteCard(page, name);
    await expect(card).toBeVisible();
    await expect(card.locator("img")).toHaveCount(0);
    await expect(card).toContainText(
      "16/08/2026 (incluído) até 17/08/2026 (excluído)",
    );
    await expect(card).toContainText("Centro (a001)");
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await page.screenshot({
      path: screenshotPath(info, "evolution-favorites.png"),
      fullPage: true,
    });
    let queryCount = 0;
    page.on("request", (request) => {
      if (request.url().endsWith("/assistant/query")) queryCount += 1;
    });
    await card
      .getByRole("button", { name: "Abrir cálculo registrado" })
      .click();
    await expect(
      page.getByTestId("answer").filter({ hasText: original.question }).first(),
    ).toContainText(money(original.result!.totals!.revenue_cents));
    expect(queryCount).toBe(0);
    await navigation(page, "Favoritos");
    const response = page.waitForResponse((reply) =>
      reply.url().endsWith(`/favorites/${saved.id}/run`),
    );
    await favoriteCard(page, name)
      .getByRole("button", { name: "Executar novamente" })
      .click();
    const rerun = await response;
    expect(rerun.status()).toBe(200);
    const next: Answer = await rerun.json();
    expect(next.id).not.toBe(original.id);
    expect(next.request_id).not.toBe(original.request_id);
    expect(next.conversation_id).not.toBe(original.conversation_id);
    expect(next.plan).toEqual(original.plan);
    expect(next.result?.totals).toEqual(original.result?.totals);
    expect(queryCount).toBe(0);
    await expect(page.getByTestId("answer").last()).toContainText("dataset");
    expect(
      await (await page.request.get(`/api/answers/${original.id}`)).json(),
    ).toEqual(original);
    await navigation(page, "Favoritos");
    const renamed = `Receita fixa ${saved.id.slice(0, 8)}`;
    const rename = favoriteCard(page, name).getByRole("button", {
      name: "Renomear",
      exact: true,
    });
    await rename.focus();
    await page.keyboard.press("Enter");
    await expect(page.getByLabel("Novo nome do favorito")).toBeFocused();
    await page.getByRole("button", { name: "Cancelar alteração" }).click();
    await expect(rename).toBeFocused();
    await rename.press("Enter");
    await page.getByLabel("Novo nome do favorito").fill(renamed);
    await page.getByRole("button", { name: "Confirmar novo nome" }).click();
    await expect(favoriteCard(page, renamed)).toBeVisible();
    await favoriteCard(page, renamed)
      .getByRole("button", { name: "Excluir", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "Confirmar exclusão" }),
    ).toBeFocused();
    await expect(
      page.getByRole("group", { name: "Confirmar exclusão do favorito" }),
    ).toContainText("continua no histórico");
    await page.getByRole("button", { name: "Manter favorito" }).click();
    await expect(
      favoriteCard(page, renamed).getByRole("button", {
        name: "Excluir",
        exact: true,
      }),
    ).toBeFocused();
    await expect(favoriteCard(page, renamed)).toBeVisible();
    await favoriteCard(page, renamed)
      .getByRole("button", { name: "Excluir", exact: true })
      .click();
    const deleted = page.waitForResponse((reply) =>
      reply.url().endsWith(`/favorites/${saved.id}/delete`),
    );
    await page.getByRole("button", { name: "Confirmar exclusão" }).click();
    expect((await deleted).status()).toBe(204);
    await expect(favoriteCard(page, renamed)).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Recarregar favoritos" }),
    ).toBeFocused();
    expect(
      (await page.request.get(`/api/answers/${original.id}`)).status(),
    ).toBe(200);
  } finally {
    await removeFavorite(page, saved);
  }
});

test("lista autorizada tardia não reaparece após logout e outra conta", async ({
  page,
}) => {
  await login(page);
  const answer = await ask(page, "Quanto vendi ontem?");
  const saved = await save(page, `Resposta tardia ${answer.id.slice(0, 8)}`);
  await navigation(page, "Sair");
  let release = () => {};
  let captured = () => {};
  let delivered = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  const ready = new Promise<void>((resolve) => {
    captured = resolve;
  });
  const finished = new Promise<void>((resolve) => {
    delivered = resolve;
  });
  let holdFirst = true;
  await page.route("**/api/favorites", async (route) => {
    if (route.request().method() === "GET" && holdFirst) {
      holdFirst = false;
      const response = await route.fetch();
      captured();
      await held;
      await route.fulfill({ response });
      delivered();
    } else await route.continue();
  });
  try {
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Análise de vendas", exact: true }),
    ).toBeVisible();
    await ready;
    await navigation(page, "Sair");
    await expect(
      page.getByRole("heading", { name: "Entrar", exact: true }),
    ).toBeVisible();
    await page.getByRole("radio", { name: /Gerente · Brisa Casa/ }).check();
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Análise de vendas", exact: true }),
    ).toBeVisible();
    await navigation(page, "Favoritos");
    await expect(
      page.getByRole("button", { name: "Recarregar favoritos" }),
    ).toBeEnabled();
    release();
    await finished;
    await page.evaluate(
      () =>
        new Promise<void>((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
        ),
    );
    await expect(favoriteCard(page, saved.name)).toHaveCount(0);
    await expect(page.getByTestId("answer")).toHaveCount(0);
    await navigation(page, "Sair");
    await expect(
      page.getByRole("heading", { name: "Entrar", exact: true }),
    ).toBeVisible();
    await page.getByRole("radio", { name: /Gerente · Aurora Casa/ }).check();
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Análise de vendas", exact: true }),
    ).toBeVisible();
    await removeFavorite(page, saved);
  } finally {
    release();
  }
});

test("revisão de outra aba retorna 409, mantém edição e permite recarregar", async ({
  page,
}) => {
  await login(page);
  const answer = await ask(page, "Quanto vendi ontem?");
  const saved = await save(page, `Duas abas ${answer.id.slice(0, 8)}`);
  try {
    await navigation(page, "Favoritos");
    const card = favoriteCard(page, saved.name);
    await card.getByRole("button", { name: "Renomear" }).click();
    const field = page.getByLabel("Novo nome do favorito");
    await field.fill("Minha edição preservada");
    const currentSession = await session(page);
    const other = await post(
      page,
      `/favorites/${saved.id}/rename`,
      { revision: saved.revision, name: "Alterado em outra aba" },
      currentSession.csrf_token,
    );
    expect(other.status()).toBe(200);
    const stale = page.waitForResponse((reply) =>
      reply.url().endsWith(`/favorites/${saved.id}/rename`),
    );
    await page.getByRole("button", { name: "Confirmar novo nome" }).click();
    expect((await stale).status()).toBe(409);
    await expect(field).toHaveValue("Minha edição preservada");
    await expect(
      page.getByRole("button", { name: "Confirmar novo nome" }),
    ).toBeDisabled();
    await page.getByRole("button", { name: "Recarregar estado atual" }).click();
    await expect(favoriteCard(page, "Alterado em outra aba")).toBeVisible();
    await expect(field).toHaveValue("Minha edição preservada");
    await expect(
      page.getByRole("button", { name: "Confirmar novo nome" }),
    ).toBeEnabled();
  } finally {
    await removeFavorite(page, saved);
  }
});

test("favoritos usam sessão e CSRF pelo proxy e isolam contas", async ({
  page,
  context,
}) => {
  await login(page);
  const answer = await ask(page, "Quanto vendi ontem?");
  const saved = await save(page, `Privado ${answer.id.slice(0, 8)}`);
  const currentSession = await session(page);
  const invalid = await post(
    page,
    `/favorites/${saved.id}/rename`,
    { revision: saved.revision, name: "Inválido" },
    "csrf-invalido",
  );
  expect(invalid.status()).toBe(403);
  const tampered = await post(
    page,
    "/favorites",
    {
      answer_id: answer.id,
      name: "Adulterado",
      plan: answer.plan,
      schema_version: 99,
    },
    currentSession.csrf_token,
  );
  expect(tampered.status()).toBe(422);
  await navigation(page, "Sair");
  await expect(
    page.getByRole("heading", { name: "Entrar", exact: true }),
  ).toBeVisible();
  await page.getByRole("radio", { name: /Gerente · Brisa Casa/ }).check();
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Análise de vendas", exact: true }),
  ).toBeVisible();
  const otherSession = await session(page);
  for (const path of [`/favorites/${saved.id}`, `/answers/${answer.id}`]) {
    const rejected = await page.request.get("/api" + path);
    expect([403, 404]).toContain(rejected.status());
    expect(await rejected.text()).not.toContain(saved.name);
    expect(await rejected.text()).not.toContain("store_references");
  }
  const rejectedRun = await post(
    page,
    `/favorites/${saved.id}/run`,
    { revision: saved.revision },
    otherSession.csrf_token,
  );
  expect([403, 404]).toContain(rejectedRun.status());
  await navigation(page, "Favoritos");
  await expect(favoriteCard(page, saved.name)).toHaveCount(0);
  await context.clearCookies();
  await page.getByRole("button", { name: "Recarregar favoritos" }).click();
  await expect(
    page.getByRole("heading", { name: "Entrar", exact: true }),
  ).toBeVisible();
  await expect(page.getByTestId("favorite")).toHaveCount(0);
  await page.getByRole("radio", { name: /Gerente · Aurora Casa/ }).check();
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Análise de vendas", exact: true }),
  ).toBeVisible();
  await removeFavorite(page, saved);
});

test("esclarecimento restaura após refresh, mostra escopo e conclui offline", async ({
  page,
}, info) => {
  await login(page);
  const answer = await ask(page, "Receita da loja Centro");
  expect(answer.status).toBe("needs_clarification");
  expect(answer.plan).toBeNull();
  const pending = answer.pending_clarification!;
  expect(pending.missing_field).toBe("period");
  expect(pending.partial_plan.metric).toBe("revenue");
  expect(pending.partial_plan.store_ids).toEqual(["a001"]);
  await expect(
    page.getByRole("heading", { name: "Qual período deseja consultar?" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Qual período deseja consultar?" }),
  ).toBeVisible();
  const panel = page.locator(".clarification-panel");
  await panel.getByRole("radio", { name: /^Ontem/i }).check();
  await expect(panel.getByLabel("Escopo a confirmar")).toContainText(
    "Receita líquida",
  );
  await expect(panel.getByLabel("Escopo a confirmar")).toContainText(
    "Centro (a001)",
  );
  await expect(panel.getByLabel("Escopo a confirmar")).toContainText(
    "16/08/2026 (incluído) até 17/08/2026 (excluído)",
  );
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.screenshot({
    path: screenshotPath(info, "evolution-pending.png"),
    fullPage: true,
  });
  const response = page.waitForResponse((reply) =>
    reply
      .url()
      .endsWith(
        `/conversations/${answer.conversation_id}/clarification/respond`,
      ),
  );
  await panel.getByRole("button", { name: "Confirmar escolha" }).click();
  const reply = await response;
  expect(reply.status()).toBe(200);
  const resolved: Answer = await reply.json();
  expect(resolved.result?.scope.map((store) => store.id)).toEqual(["a001"]);
  expect(resolved.plan?.metric).toBe("revenue");
  expect(resolved.plan?.period).toEqual({
    start: "2026-08-16",
    end: "2026-08-17",
  });
  await expect(page.getByTestId("answer").last()).toContainText(
    money(resolved.result!.totals!.revenue_cents),
  );
  await expect(
    page.getByRole("button", { name: "Confirmar escolha" }),
  ).toHaveCount(0);
  const currentSession = await session(page);
  const replay = await post(
    page,
    `/conversations/${answer.conversation_id}/clarification/respond`,
    {
      pending_id: pending.id,
      revision: pending.revision,
      choice_id: pending.choices[0].id,
    },
    currentSession.csrf_token,
  );
  expect(replay.status()).toBe(409);
});

test("pendência nova invalida a escolha anterior; cancelar e logout limpam controles", async ({
  page,
}) => {
  await login(page);
  const first = await ask(page, "Receita da loja Centro");
  const firstPending = first.pending_clarification!;
  const second = await ask(page, "Pedidos da loja Centro");
  const secondPending = second.pending_clarification!;
  expect(secondPending.id).not.toBe(firstPending.id);
  expect(secondPending.partial_plan.metric).toBe("orders");
  const currentSession = await session(page);
  const old = await post(
    page,
    `/conversations/${first.conversation_id}/clarification/respond`,
    {
      pending_id: firstPending.id,
      revision: firstPending.revision,
      choice_id: firstPending.choices[0].id,
    },
    currentSession.csrf_token,
  );
  expect(old.status()).toBe(409);
  const cancel = page.waitForResponse((reply) =>
    reply
      .url()
      .endsWith(
        `/conversations/${second.conversation_id}/clarification/cancel`,
      ),
  );
  await page.getByRole("button", { name: "Cancelar esclarecimento" }).click();
  expect((await cancel).status()).toBe(200);
  await expect(
    page.getByRole("button", { name: "Confirmar escolha" }),
  ).toHaveCount(0);
  const detail = await page.request.get(
    `/api/conversations/${second.conversation_id}`,
  );
  expect(
    ((await detail.json()).pending_clarification as PendingClarification)
      .status,
  ).toBe("cancelled");
  const qualified = await ask(page, "Quanto vendi ontem somente em dinheiro?");
  expect(qualified.result).toBeNull();
  expect(qualified.plan).toBeNull();
  expect(qualified.pending_clarification ?? null).toBeNull();
  await expect(
    page.getByRole("button", { name: "Confirmar escolha" }),
  ).toHaveCount(0);
  await ask(page, "Receita da loja Centro");
  await expect(
    page.getByRole("button", { name: "Confirmar escolha" }),
  ).toBeVisible();
  await navigation(page, "Sair");
  await expect(
    page.getByRole("heading", { name: "Entrar", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".clarification-panel")).toHaveCount(0);
  await page.getByRole("radio", { name: /Gerente · Brisa Casa/ }).check();
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Análise de vendas", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".clarification-panel")).toHaveCount(0);
});

test("novos controles usam teclado e cabem em 360px e ampliação de 200%", async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await login(page);
  const answer = await ask(page, "Receita da loja Centro");
  const radio = page.getByRole("radio", { name: /^Ontem/i });
  await radio.focus();
  await page.keyboard.press("Space");
  await expect(radio).toBeChecked();
  await expect(
    page.getByRole("button", { name: "Confirmar escolha" }),
  ).toBeEnabled();
  const fits = () =>
    page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    );
  expect(await fits()).toBe(true);
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
  await page.screenshot({
    path: screenshotPath(info, "evolution-mobile.png"),
    fullPage: true,
  });
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  expect(await fits()).toBe(true);
  await page.evaluate(() => {
    document.documentElement.style.zoom = "";
  });
  await page.getByRole("button", { name: "Cancelar esclarecimento" }).click();
  await expect(
    page.getByRole("button", { name: "Confirmar escolha" }),
  ).toHaveCount(0);
  const currentSession = await session(page);
  expect(
    (
      await post(
        page,
        `/conversations/${answer.conversation_id}/clarification/cancel`,
        {
          pending_id: answer.pending_clarification!.id,
          revision: answer.pending_clarification!.revision,
        },
        currentSession.csrf_token,
      )
    ).status(),
  ).toBe(409);
});

test("CSRF de sessão substituída limpa dados protegidos na interface", async ({
  page,
}) => {
  await login(page);
  const answer = await ask(page, "Quanto vendi ontem?");
  const saved = await save(page, `Sessão substituída ${answer.id.slice(0, 8)}`);
  try {
    await navigation(page, "Favoritos");
    await favoriteCard(page, saved.name)
      .getByRole("button", { name: "Renomear" })
      .click();
    await page
      .getByLabel("Novo nome do favorito")
      .fill("Edição da sessão anterior");
    const currentSession = await session(page);
    expect(
      (
        await post(page, "/auth/logout", {}, currentSession.csrf_token)
      ).status(),
    ).toBe(200);
    const replacement = await post(page, "/auth/login", {
      email: "gerente.a@demo.local",
      password: "LojaDemo!2026",
    });
    expect(replacement.status()).toBe(200);
    const denied = page.waitForResponse((reply) =>
      reply.url().endsWith(`/favorites/${saved.id}/rename`),
    );
    await page.getByRole("button", { name: "Confirmar novo nome" }).click();
    expect((await denied).status()).toBe(403);
    await expect(page.getByTestId("favorite")).toHaveCount(0);
    await expect(page.getByTestId("answer")).toHaveCount(0);
    await expect(page.locator(".clarification-panel")).toHaveCount(0);
    const csrfAlert = page
      .getByRole("alert")
      .filter({ hasText: "Token CSRF inválido" });
    await expect(csrfAlert).toBeVisible();
    await expect(csrfAlert).toContainText("Recarregue a página.");
  } finally {
    await removeFavorite(page, saved);
  }
});
