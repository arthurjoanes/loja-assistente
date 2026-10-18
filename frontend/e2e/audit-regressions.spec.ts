import { expect, test, type Page } from "@playwright/test";
import {
  exclusiveEnd,
  includedEnd,
  validPeriod,
} from "../src/features/assistant/period-selection";
import type { Answer, PendingClarification } from "../src/lib/contracts";
import {
  analysisReducer,
  emptyAnalysis,
} from "../src/features/assistant/conversation-state";

const stamp = "2026-10-13T01:30:00Z";
const conversation = {
  id: "c",
  title: "Pergunta sintética",
  created_at: stamp,
};
const pending: PendingClarification = {
  id: "pending",
  revision: 1,
  status: "pending",
  original_question: "Receita da loja Centro",
  partial_plan: {
    intent: "aggregate",
    metric: "revenue",
    store_ids: ["s"],
    period: null,
    comparison: null,
    grouping: null,
    limit: 10,
  },
  missing_field: "period",
  choices: [
    {
      id: "yesterday",
      label: "Ontem",
      period: { start: "2026-08-16", end: "2026-08-17" },
      store_ids: null,
    },
  ],
  created_at: new Date().toISOString(),
  expires_at: new Date(Date.now() + 600000).toISOString(),
  schema_version: 1,
  mode: "demo",
  reference_date: "2026-08-17",
};
const answer = (id = "a"): Answer => ({
  id,
  conversation_id: "c",
  question: "Pergunta sintética " + id,
  status: "unsupported",
  message: "Resposta sintética sem consulta externa",
  mode: "demo",
  plan: null,
  result: null,
  request_id: "request",
  created_at: stamp,
});

async function mock(page: Page, clarification = false) {
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown;
    if (path === "/api/auth/me")
      json = {
        user: {
          id: "u",
          name: "Pessoa sintética",
          email: "u@example.invalid",
          role: "manager",
          organization: { id: "t", name: "Tenant sintético" },
          stores: [{ id: "s", name: "Centro" }],
        },
        csrf_token: "synthetic",
        reference_date: "2026-08-17",
        dataset_version: "synthetic",
        llm_available: false,
      };
    else if (path === "/api/conversations/page")
      json = {
        items: [
          {
            ...conversation,
            pending_clarification: clarification ? pending : null,
          },
        ],
        next_cursor: null,
        has_more: false,
      };
    else if (path === "/api/conversations/c")
      json = {
        ...conversation,
        messages: [answer()],
        pending_clarification: clarification ? pending : null,
        messages_next_cursor: null,
      };
    else if (path === "/api/favorites") json = [];
    else
      return route.fulfill({
        status: 404,
        json: { detail: "Endpoint não incluído nesta fixture sintética" },
      });
    await route.fulfill({ json });
  });
}

for (const field of ["question", "period"] as const) {
  test(`esclarecimento antigo não substitui edição de ${field}`, async ({
    page,
  }) => {
    await mock(page, true);
    let release = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    let requested = () => {};
    const ready = new Promise<void>((resolve) => {
      requested = resolve;
    });
    await page.route("**/api/conversations/c", async (route) => {
      requested();
      await held;
      await route.fallback();
    });
    await page.goto("/");
    await ready;
    if (field === "question")
      await page
        .getByLabel("Pergunta", { exact: true })
        .fill("Receita da semana");
    else await page.getByLabel("Período", { exact: true }).selectOption("week");
    const restored = page.waitForResponse((response) =>
      response.url().endsWith("/conversations/c"),
    );
    release();
    await restored;
    await page.evaluate(
      () =>
        new Promise<void>((resolve) =>
          requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
        ),
    );
    if (field === "question")
      await expect(page.getByLabel("Pergunta", { exact: true })).toHaveValue(
        "Receita da semana",
      );
    else
      await expect(page.getByLabel("Período", { exact: true })).toHaveValue(
        "week",
      );
    await expect(
      page.getByRole("heading", { name: "Qual período deseja consultar?" }),
    ).toHaveCount(0);
  });
}

test("LOJ-02: favorites failure preserves history and pending clarification", async ({
  page,
}) => {
  await mock(page, true);
  await page.route("**/api/favorites", (route) =>
    route.fulfill({
      status: 503,
      json: { detail: "Favoritos temporariamente indisponíveis" },
    }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Qual período deseja consultar?" }),
  ).toBeVisible();
  await page.locator(".history-menu > summary").click();
  await expect(
    page.getByRole("navigation", { name: "Histórico pessoal" }),
  ).toContainText("Pergunta sintética");
  await page.getByRole("button", { name: "Favoritos", exact: true }).click();
  await expect(
    page.getByText("Favoritos temporariamente indisponíveis").first(),
  ).toBeVisible();
});

test("LOJ-02: history failure has an explicit recovery and is not empty content", async ({
  page,
}) => {
  await mock(page);
  let fail = true;
  await page.route("**/api/conversations/page", (route) =>
    fail
      ? route.fulfill({
          status: 503,
          json: { detail: "Histórico indisponível" },
        })
      : route.fulfill({
          json: { items: [conversation], next_cursor: null, has_more: false },
        }),
  );
  await page.goto("/");
  await page.locator(".history-menu > summary").click();
  await expect(page.getByText("Histórico indisponível")).toBeVisible();
  await expect(page.getByText("Nenhuma conversa", { exact: true })).toHaveCount(
    0,
  );
  fail = false;
  await page.getByRole("button", { name: "Recarregar histórico" }).click();
  await expect(
    page.getByRole("navigation", { name: "Histórico pessoal" }),
  ).toContainText("Pergunta sintética");
});

test("LOJ-01: a lost query response recovers its durable intent without posting twice", async ({
  page,
}) => {
  await mock(page);
  let key = "";
  let posts = 0;
  await page.route("**/api/assistant/query", async (route) => {
    posts++;
    key = route.request().postDataJSON().client_request_id;
    await route.abort("failed");
  });
  await page.route("**/api/assistant/requests/*", (route) => {
    expect(route.request().url()).toContain(key);
    return route.fulfill({ json: answer("recovered") });
  });
  await page.goto("/");
  await page
    .getByLabel("Pergunta", { exact: true })
    .fill("Quanto vendi ontem?");
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  await expect(
    page.getByText(/Não foi possível confirmar a execução/),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Enviar pergunta" }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Recarregar estado atual", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Pergunta sintética recovered" }),
  ).toBeVisible();
  expect(posts).toBe(1);
  expect(key).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
  );
});

test("LOJ-03: previous conversations and the 101st response remain reachable", async ({
  page,
}) => {
  await mock(page);
  await page.route("**/api/conversations/page*", (route) =>
    route.fulfill({
      json: new URL(route.request().url()).searchParams.has("cursor")
        ? {
            items: [{ ...conversation, id: "old", title: "Conversa antiga" }],
            next_cursor: null,
            has_more: false,
          }
        : {
            items: Array.from({ length: 50 }, (_, i) => ({
              ...conversation,
              id: i ? "c" + i : "c",
              title: "Conversa " + i,
            })),
            next_cursor: "older",
            has_more: true,
          },
    }),
  );
  await page.route("**/api/conversations/c", (route) =>
    route.fulfill({
      json: {
        ...conversation,
        messages: Array.from({ length: 100 }, (_, i) => answer("a" + (i + 1))),
        messages_next_cursor: "older",
      },
    }),
  );
  await page.route("**/api/conversations/c/messages?*", (route) =>
    route.fulfill({
      json: { items: [answer("a0")], next_cursor: null, has_more: false },
    }),
  );
  await page.goto("/");
  await page.locator(".history-menu > summary").click();
  await page
    .getByRole("button", { name: "Carregar conversas anteriores" })
    .click();
  await expect(
    page.getByRole("button", { name: /Conversa antiga/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: /^Conversa 0 / }).click();
  await page
    .getByRole("button", { name: "Carregar respostas anteriores" })
    .click();
  await expect(page.locator("#result-selector option")).toHaveCount(101);
  await page.getByLabel("Resultado selecionado").selectOption("a0");
  await expect(
    page.getByRole("heading", { name: "Pergunta sintética a0", exact: true }),
  ).toBeVisible();
});

test("LOJ-01: navigation and favorites cannot clear an uncertain query", async ({
  page,
}) => {
  await mock(page);
  let posts = 0;
  let detailReads = 0;
  await page.route("**/api/assistant/query", (route) => {
    posts++;
    return route.abort("failed");
  });
  await page.route("**/api/conversations/c", (route) => {
    detailReads++;
    return route.fulfill({
      json: {
        ...conversation,
        messages: [answer("other")],
        messages_next_cursor: null,
      },
    });
  });
  await page.route("**/api/assistant/requests/*", (route) =>
    route.fulfill({
      json: { ...answer("recovered"), conversation_id: "original" },
    }),
  );
  await page.goto("/");
  await page
    .getByLabel("Pergunta", { exact: true })
    .fill("Quanto vendi ontem?");
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  await expect(
    page.getByText(/Não foi possível confirmar a execução/),
  ).toBeVisible();
  await page.locator(".history-menu > summary").click();
  await page
    .getByRole("navigation", { name: "Histórico pessoal" })
    .getByRole("button")
    .first()
    .click();
  await expect(page.getByText(/Há uma consulta sem confirmação/)).toBeVisible();
  expect(detailReads).toBe(0);
  await page.getByRole("button", { name: "Favoritos", exact: true }).click();
  await page.getByRole("button", { name: "Análises", exact: true }).click();
  await expect(page.getByLabel("Pergunta", { exact: true })).toHaveValue(
    "Quanto vendi ontem?",
  );
  await expect(
    page.getByRole("button", { name: "Enviar pergunta" }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Recarregar estado atual", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Pergunta sintética recovered",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Pergunta sintética other", { exact: true }),
  ).toHaveCount(0);
  expect(posts).toBe(1);
});

test("LOJ-01: a missing admission resends the same intent with an accurate confirmation", async ({
  page,
}) => {
  await mock(page);
  const posts: object[] = [];
  await page.route("**/api/assistant/query", (route) => {
    posts.push(route.request().postDataJSON());
    return posts.length === 1
      ? route.abort("failed")
      : route.fulfill({ json: answer("confirmed") });
  });
  await page.route("**/api/assistant/requests/*", (route) =>
    route.fulfill({ status: 404, json: { detail: "Intenção não encontrada" } }),
  );
  await page.goto("/");
  await page
    .getByLabel("Pergunta", { exact: true })
    .fill("Quanto vendi ontem?");
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  await expect(
    page.getByText(/Não foi possível confirmar a execução/),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Recarregar estado atual", exact: true })
    .click();
  await expect(
    page.getByText(
      "A mesma intenção foi enviada com segurança e sua resposta foi confirmada.",
    ),
  ).toBeVisible();
  expect(posts).toHaveLength(2);
  expect(posts[1]).toEqual(posts[0]);
});

test("LOJ-01: starting another analysis abandons local recovery without another automatic request", async ({
  page,
}) => {
  await mock(page);
  const posts: { question: string; client_request_id: string }[] = [];
  let recoveries = 0;
  await page.route("**/api/assistant/query", (route) => {
    posts.push(route.request().postDataJSON());
    return posts.length === 1
      ? route.abort("failed")
      : route.fulfill({
          json: { ...answer("new"), question: posts[1].question },
        });
  });
  await page.route("**/api/assistant/requests/*", (route) => {
    recoveries++;
    return route.fulfill({ status: 409, json: { detail: "Incerto" } });
  });
  await page.goto("/");
  await page.getByLabel("Pergunta", { exact: true }).fill("Consulta antiga");
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  await expect(
    page.getByText(/Não foi possível confirmar a execução/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Nova análise", exact: true }).click();
  await expect(page.getByLabel("Pergunta", { exact: true })).toHaveValue("");
  expect(posts).toHaveLength(1);
  await page
    .getByLabel("Pergunta", { exact: true })
    .fill("Nova pergunta explícita");
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  await expect(
    page.getByRole("heading", { name: "Nova pergunta explícita", exact: true }),
  ).toBeVisible();
  expect(posts).toHaveLength(2);
  expect(posts[1].client_request_id).not.toBe(posts[0].client_request_id);
  expect(recoveries).toBe(0);
});

test("LOJ-01: changing accounts clears an uncertain intent without recovering or reposting it", async ({
  page,
}) => {
  await mock(page);
  const posts: { question: string; client_request_id: string }[] = [];
  let recoveries = 0;
  let signedOut = false;
  await page.route("**/api/conversations/page", (route) =>
    route.fulfill({
      json: {
        items: signedOut ? [] : [conversation],
        next_cursor: null,
        has_more: false,
      },
    }),
  );
  await page.route("**/api/auth/logout", (route) => {
    signedOut = true;
    return route.fulfill({ json: { ok: true } });
  });
  await page.route("**/api/auth/login", (route) =>
    route.fulfill({
      json: {
        user: {
          id: "second",
          name: "Outra pessoa",
          email: "second@example.invalid",
          role: "manager",
          organization: { id: "other", name: "Outro tenant" },
          stores: [{ id: "other-store", name: "Norte" }],
        },
        csrf_token: "second-csrf",
        reference_date: "2026-08-17",
        dataset_version: "synthetic",
        llm_available: false,
      },
    }),
  );
  await page.route("**/api/assistant/query", (route) => {
    posts.push(route.request().postDataJSON());
    return posts.length === 1
      ? route.abort("failed")
      : route.fulfill({
          json: { ...answer("second-account"), question: posts[1].question },
        });
  });
  await page.route("**/api/assistant/requests/*", (route) => {
    recoveries++;
    return route.fulfill({ status: 404, json: { detail: "Não encontrada" } });
  });
  await page.goto("/");
  await page
    .getByLabel("Pergunta", { exact: true })
    .fill("Pergunta da primeira conta");
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  await expect(
    page.getByText(/Não foi possível confirmar a execução/),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByText("Outra pessoa", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Pergunta", { exact: true })).toHaveValue("");
  await page
    .getByLabel("Pergunta", { exact: true })
    .fill("Pergunta da segunda conta");
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Pergunta da segunda conta",
      exact: true,
    }),
  ).toBeVisible();
  expect(posts).toHaveLength(2);
  expect(posts[1].client_request_id).not.toBe(posts[0].client_request_id);
  expect(posts[1].question).toBe("Pergunta da segunda conta");
  expect(recoveries).toBe(0);
});

test("LOJ-01: receiving a different conversation cannot merge its answers or pagination cursor", () => {
  const state = {
    ...emptyAnalysis(),
    conversationId: "other",
    answers: [answer("old")],
    messagesNextCursor: "other-cursor",
    question: "Rascunho preservado",
  };
  const next = analysisReducer(state, {
    type: "answer",
    value: answer("recovered"),
  });
  expect(next.answers.map((item) => item.id)).toEqual(["recovered"]);
  expect(next.messagesNextCursor).toBeNull();
  expect(next.question).toBe("Rascunho preservado");
});

for (const timezoneId of ["UTC", "America/Los_Angeles", "America/Sao_Paulo"]) {
  test.describe(timezoneId, () => {
    test.use({ timezoneId });
    test("LOJ-04/05: included end dates and timestamps agree", async ({
      page,
    }) => {
      await mock(page);
      await page.goto("/");
      await page.locator(".history-menu > summary").click();
      await page
        .getByRole("navigation", { name: "Histórico pessoal" })
        .getByRole("button")
        .first()
        .click();
      await expect(page.locator(".history-date").first()).toHaveText(
        "12/10/2026, 22:30",
      );
      await expect(page.locator(".calculation-version time")).toHaveText(
        "12/10/2026, 22:30",
      );
      await page.getByLabel("Período", { exact: true }).selectOption("custom");
      await page.getByLabel("Início (incluído)").fill("2024-02-29");
      await page.getByLabel("Até (incluído)").fill("2024-02-29");
      await expect(page.getByLabel("Até (incluído)")).toHaveValue("2024-02-29");
      await expect(page.getByLabel("Até (incluído)")).toHaveAttribute(
        "aria-invalid",
        "false",
      );
    });
  });
}

test("LOJ-04: civil dates cover leap years, year boundaries, 90 days and upper bound", () => {
  for (const [included, exclusive] of [
    ["2024-02-29", "2024-03-01"],
    ["2026-12-31", "2027-01-01"],
    ["9999-12-30", "9999-12-31"],
  ]) {
    expect(exclusiveEnd(included)).toBe(exclusive);
    expect(includedEnd(exclusive)).toBe(included);
    expect(validPeriod({ start: included, end: exclusive })).toBe(true);
  }
  expect(exclusiveEnd("9999-12-31")).toBe("");
  expect(exclusiveEnd("")).toBe("");
  expect(
    validPeriod({ start: "2026-05-19", end: exclusiveEnd("2026-08-16") }),
  ).toBe(true);
  expect(
    validPeriod({ start: "2026-05-19", end: exclusiveEnd("2026-08-17") }),
  ).toBe(false);
});
