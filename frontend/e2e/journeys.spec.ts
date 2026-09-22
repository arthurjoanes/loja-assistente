import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type TestInfo } from "@playwright/test";
import type { Answer } from "../src/lib/contracts";
import { money } from "../src/lib/format";

function screenshotPath(testInfo: TestInfo, name: string) {
  return process.env.SCREENSHOT_DIR
    ? process.env.SCREENSHOT_DIR + "/" + name
    : testInfo.outputPath(name);
}

async function login(page: Page, profile = "Gerente · Aurora Casa") {
  await page.goto("/");
  await page.getByRole("radio", { name: new RegExp(profile) }).check();
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(
    page.getByRole("heading", { name: "Análise de vendas" }),
  ).toBeVisible();
}
async function ask(page: Page, question: string): Promise<Answer> {
  if (!(await page.getByLabel("Pergunta", { exact: true }).isVisible()))
    await page.getByRole("button", { name: "Editar pergunta" }).click();
  const response = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/assistant/query") &&
      response.request().method() === "POST",
  );
  await page.getByLabel("Pergunta", { exact: true }).fill(question);
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  const reply = await response;
  expect(reply.status()).toBe(200);
  const answer: Answer = await reply.json();
  await expect(page.getByTestId("answer").last()).toContainText(question);
  return answer;
}

test("gestor consulta receita, evidência, ranking, comparação e continuação", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await login(page);
  await page.screenshot({
    path: screenshotPath(testInfo, "inicio.png"),
    fullPage: true,
  });
  await expect(
    page.getByText("Demo sem IA", { exact: true }).last(),
  ).toBeVisible();
  const revenue = await ask(page, "Quanto vendi ontem?");
  expect(revenue.status).toBe("ready");
  await expect(
    page
      .getByTestId("answer")
      .last()
      .getByRole("heading", { name: revenue.question, exact: true }),
  ).toBeVisible();
  expect(revenue.result?.scope.map((store) => store.id)).toEqual(["a001"]);
  expect(revenue.result?.period).toEqual({
    start: "2026-08-16",
    end: "2026-08-17",
  });
  await expect(page.getByTestId("answer").last()).toContainText(
    money(revenue.result!.totals!.revenue_cents),
  );
  const evidenceResponse = page.waitForResponse((response) =>
    response.url().endsWith("/answers/" + revenue.id + "/evidence"),
  );
  await page.getByText("Cálculo", { exact: true }).click();
  expect((await evidenceResponse).status()).toBe(200);
  await expect(
    page.getByText(revenue.request_id, { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Totais por dia", { exact: true })).toBeVisible();
  await page.screenshot({
    path: screenshotPath(testInfo, "consulta-com-evidencia.png"),
    fullPage: true,
  });

  const ranking = await ask(
    page,
    "Quais os 5 produtos com maior receita nos últimos 7 dias?",
  );
  expect(ranking.result?.intent).toBe("ranking");
  expect(ranking.result?.rows.length).toBe(5);
  await expect(page.getByTestId("answer").last()).toContainText(
    "O total inclui todos os produtos das lojas e do período consultados.",
  );
  await page.getByRole("button", { name: "Tabela", exact: true }).click();
  await expect(
    page.getByText("Produtos classificados pela métrica consultada", {
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Gráfico", exact: true }).click();

  const daily = await ask(
    page,
    "Mostre a evolução diária da receita nos últimos 7 dias",
  );
  expect(daily.result?.intent).toBe("daily");
  expect(daily.result?.rows.length).toBe(7);
  expect(
    daily
      .result!.rows.reduce(
        (total, row) => total + BigInt(row.revenue_cents),
        0n,
      )
      .toString(),
  ).toBe(daily.result?.totals?.revenue_cents);
  const dailyCard = page.getByTestId("answer").last();
  await expect(
    dailyCard.getByRole("heading", { name: daily.question, exact: true }),
  ).toBeVisible();
  await expect(
    dailyCard.getByRole("img", { name: /^Evolução diária\./ }),
  ).toBeVisible();
  await dailyCard.getByRole("button", { name: "Tabela", exact: true }).click();
  await expect(
    dailyCard.getByText("Série por dia comercial", { exact: true }),
  ).toBeVisible();
  await dailyCard.getByRole("button", { name: "Gráfico", exact: true }).click();
  await dailyCard.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: screenshotPath(testInfo, "evolucao-diaria.png"),
    fullPage: true,
  });

  const comparison = await ask(
    page,
    "Compare a receita dos últimos 7 dias com o período anterior",
  );
  expect(comparison.result?.comparison?.period).toEqual({
    start: "2026-08-03",
    end: "2026-08-10",
  });
  await expect(page.getByTestId("answer").last()).toContainText(
    "período anterior",
  );
  const continuation = await ask(page, "E nos sete dias anteriores?");
  expect(continuation.result?.period).toEqual({
    start: "2026-08-03",
    end: "2026-08-10",
  });
  await page.getByRole("button", { name: "Atendimentos" }).click();
  await expect(
    page.getByRole("heading", { name: "Atendimentos", level: 1, exact: true }),
  ).toBeVisible();
  await page
    .getByRole("row")
    .filter({ hasText: revenue.request_id })
    .locator("summary")
    .click();
  await expect(
    page.getByText(revenue.request_id, { exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("paráfrase e cortesia preservam cálculo; qualificador recusado não vira total", async ({
  page,
}, testInfo) => {
  await login(page);
  const canonical = await ask(page, "Quanto vendi ontem?");
  expect(canonical.status).toBe("ready");
  for (const question of [
    "Quanto eu vendi ontem?",
    "Me mostra o faturamento de ontem",
    "Só queria saber a receita de ontem",
  ]) {
    const answer = await ask(page, question);
    expect(answer.status).toBe("ready");
    expect(answer.plan).toEqual(canonical.plan);
    expect(answer.result?.totals).toEqual(canonical.result?.totals);
    await expect(page.getByTestId("answer").last()).toContainText(
      money(canonical.result!.totals!.revenue_cents),
    );
  }
  const qualified = await ask(
    page,
    "Só queria saber quanto vendi ontem somente em dinheiro",
  );
  expect(qualified.status).toBe("needs_clarification");
  expect(qualified.plan).toBeNull();
  expect(qualified.result).toBeNull();
  const greeting = await ask(page, "Oi!");
  expect(greeting.result).toBeNull();
  await expect(page.getByTestId("answer").last()).toContainText(
    "Qual indicador e período",
  );
  const recovered = await ask(page, "Quanto eu vendi ontem?");
  expect(recovered.result?.totals).toEqual(canonical.result?.totals);
  await page.screenshot({
    path: screenshotPath(testInfo, "language-proof.png"),
    fullPage: true,
  });
});

test("login e análise atendem verificações automatizadas de acessibilidade", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Entrar" })).toBeVisible();
  expect
    .soft(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    )
    .toEqual([]);
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(
    page.getByRole("heading", { name: "Análise de vendas" }),
  ).toBeVisible();
  expect
    .soft(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    )
    .toEqual([]);
  await ask(page, "Quanto vendi ontem?");
  expect
    .soft(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    )
    .toEqual([]);
});

test("troca de usuário isola histórico, resposta e evidência no backend", async ({
  page,
}, testInfo) => {
  await login(page);
  const own = await ask(page, "Quanto vendi ontem?");
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page.getByRole("heading", { name: "Entrar" })).toBeVisible();
  await page.getByRole("radio", { name: /Gerente · Brisa Casa/ }).check();
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(
    page.getByRole("heading", { name: "Análise de vendas" }),
  ).toBeVisible();
  expect(await page.getByTestId("answer").count()).toBe(0);
  const conversations = await page.request.get("/api/conversations");
  expect(
    (await conversations.json()).map((item: { id: string }) => item.id),
  ).not.toContain(own.conversation_id);
  for (const path of [
    "/conversations/" + own.conversation_id,
    "/answers/" + own.id,
    "/answers/" + own.id + "/evidence",
  ]) {
    const forbidden = await page.request.get("/api" + path);
    expect([403, 404]).toContain(forbidden.status());
    const body = await forbidden.text();
    expect(body).not.toContain(own.request_id);
    expect(body).not.toContain("revenue_cents");
  }
  const other = await ask(page, "Quanto vendi ontem?");
  expect(other.result?.scope.map((store) => store.id)).toEqual(["b001"]);
  expect(other.result?.totals?.revenue_cents).not.toBe(
    own.result?.totals?.revenue_cents,
  );
  await expect(page.getByLabel("Loja", { exact: true })).toHaveValue("b001");
  await page.screenshot({
    path: screenshotPath(testInfo, "organizacao-b.png"),
    fullPage: true,
  });
});

test("limitação, provedor indisponível e expiração têm estados recuperáveis", async ({
  page,
  context,
}) => {
  await login(page);
  const unsupported = await ask(page, "Qual foi o lucro ontem?");
  expect(unsupported.status).toBe("unsupported");
  expect(unsupported.result).toBeNull();
  const absent = await ask(page, "Quanto vendi em 2026-09-01?");
  expect(absent.result?.coverage.status).toBe("absent");
  expect(absent.result?.totals).toBeNull();
  await expect(page.getByTestId("answer").last()).toContainText(
    "Sem dados carregados",
  );
  await page.getByLabel("Interpretador", { exact: true }).selectOption("llm");
  const unavailable = page
    .getByRole("status")
    .filter({ hasText: "A interpretação com IA não está disponível" });
  await expect(unavailable).toBeVisible();
  await expect(unavailable).toContainText(
    "Selecione demonstração para continuar consultando os dados.",
  );
  await expect(
    page.getByRole("button", { name: "Enviar pergunta" }),
  ).toBeDisabled();
  await page.getByLabel("Interpretador", { exact: true }).selectOption("demo");
  await context.clearCookies();
  await page
    .getByLabel("Pergunta", { exact: true })
    .fill("Quanto vendi ontem?");
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  await expect(page.getByRole("heading", { name: "Entrar" })).toBeVisible();
  await expect(
    page.getByText("Sessão expirada. Entre novamente."),
  ).toBeVisible();
});

test("celular permite teclado, filtros e leitura sem overflow horizontal", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, "Supervisor · Aurora Casa");
  await expect(page.getByRole("button", { name: "Abrir menu" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Nova consulta", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Pergunta", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Editar pergunta" }),
  ).toHaveCount(0);
  const suggestionsBeforeQuery = await page
    .locator(".welcome")
    .evaluate((element) =>
      Boolean(
        element.compareDocumentPosition(
          document.querySelector("#query-controls")!,
        ) & Node.DOCUMENT_POSITION_FOLLOWING,
      ),
    );
  expect(suggestionsBeforeQuery).toBe(true);
  const suggestions = page.locator(".suggestions").getByRole("button");
  await expect(suggestions).toHaveCount(6);
  await page.getByRole("button", { name: "Abrir menu" }).focus();
  for (const name of [
    "Receita de ontem",
    "Ranking de produtos",
    "Evolução diária",
    "Ticket médio",
    "Comparação de períodos",
    "Unidades vendidas",
  ]) {
    await page.keyboard.press("Tab");
    await expect(
      page
        .locator(".suggestions")
        .getByRole("button", { name: new RegExp(name) }),
    ).toBeFocused();
  }
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Loja", { exact: true })).toBeFocused();
  await page.getByLabel("Loja", { exact: true }).selectOption("a002");
  await page.getByLabel("Período", { exact: true }).selectOption("week");
  const response = page.waitForResponse((response) =>
    response.url().endsWith("/api/assistant/query"),
  );
  await page
    .getByLabel("Pergunta", { exact: true })
    .fill("Quanto vendi ontem?");
  await page.getByLabel("Pergunta", { exact: true }).press("Enter");
  const answer: Answer = await (await response).json();
  expect(answer.result?.scope.map((store) => store.id)).toEqual(["a002"]);
  expect(answer.result?.period).toEqual({
    start: "2026-08-16",
    end: "2026-08-17",
  });
  await expect(page.getByTestId("answer")).toBeVisible();
  await page.getByRole("button", { name: "Recolher próxima consulta" }).click();
  await expect(page.getByLabel("Pergunta", { exact: true })).toBeHidden();
  await expect(
    page.getByRole("button", { name: "Editar pergunta" }),
  ).toBeFocused();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: screenshotPath(testInfo, "consulta-mobile.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Abrir menu" }).click();
  await expect(
    page.getByRole("button", { name: "Nova análise" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Fechar menu", exact: true }).click();
});
