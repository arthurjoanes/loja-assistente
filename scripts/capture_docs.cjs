// Captura real em Demo; requisições ao interpretador LLM são bloqueadas.
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { chromium, expect } = require("@playwright/test");

(async () => {
  const output = process.env.DOCS_SCREENSHOT_DIR;
  if (!output) throw new Error("Defina DOCS_SCREENSHOT_DIR em uma pasta nova.");
  fs.mkdirSync(output, { recursive: true });
  if (fs.readdirSync(output).length)
    throw new Error("A pasta de captura deve estar vazia.");
  const browser = await chromium.launch({ headless: true });
  const report = {
    captured_at: new Date().toISOString(),
    source_commit: process.env.SOURCE_COMMIT || null,
    application: process.env.BASE_URL || "http://localhost:3102",
    browser_version: browser.version(),
    capture_method:
      "Capturas nativas de componentes e clip; sem fullPage ou edição de pixels.",
    scope:
      "Aplicação real; gerente demo; modo demo explícito e bloqueio de mode diferente de demo; sem provedor pago.",
    queries: [],
    images: [],
    page_errors: [],
    rejected_requests: [],
  };
  try {
    const page = await browser.newPage({
      viewport: { width: 1440, height: 1000 },
      locale: "pt-BR",
      timezoneId: "America/Sao_Paulo",
      reducedMotion: "reduce",
    });
    page.on("pageerror", (error) => report.page_errors.push(error.message));
    await page.route("**/api/assistant/query", async (route) => {
      const data = route.request().postDataJSON();
      if (data.mode !== "demo") {
        report.rejected_requests.push(data.mode);
        await route.abort("blockedbyclient");
        return;
      }
      await route.continue();
    });
    const focus = {
      "inicio.png": ".welcome",
      "inicio-mobile.png": ".welcome",
      "evolucao-diaria.png": ".analysis-reading",
      "consulta-com-calculo.png": ".evidence",
      "consulta-mobile.png": ".period-summary",
      "filtro-nao-suportado.png": ".answer-block",
    };
    const capture = async (name) => {
      await page.evaluate(() => document.fonts.ready);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.evaluate(
        () =>
          new Promise((resolve) =>
            requestAnimationFrame(() => requestAnimationFrame(resolve)),
          ),
      );
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      );
      expect(overflow, `${name}: sem overflow horizontal global`).toBe(false);
      const target = path.join(output, name);
      const region = page.locator(focus[name]).last();
      let bounds = await region.boundingBox();
      expect(bounds).not.toBeNull();
      if (name === "evolucao-diaria.png") {
        const summary = await page
          .locator(".period-summary")
          .last()
          .boundingBox();
        const footnote = await page
          .locator(".chart-footnote")
          .last()
          .boundingBox();
        bounds = {
          ...bounds,
          height:
            Math.max(summary.y + summary.height, footnote.y + footnote.height) -
            bounds.y,
        };
      }
      if (page.viewportSize().width < 600)
        expect(bounds.height).toBeLessThanOrEqual(650);
      else expect(bounds.height / bounds.width).toBeLessThanOrEqual(1.1);
      if (name === "evolucao-diaria.png") {
        await page.screenshot({
          path: target,
          clip: bounds,
          animations: "disabled",
        });
      } else {
        await region.screenshot({ path: target, animations: "disabled" });
      }
      report.images.push({
        path: name,
        focus: focus[name],
        dimensions: {
          width: fs.readFileSync(target).readUInt32BE(16),
          height: fs.readFileSync(target).readUInt32BE(20),
        },
        dimension_source: "PNG IHDR",
        viewport: page.viewportSize(),
        sha256: crypto
          .createHash("sha256")
          .update(fs.readFileSync(target))
          .digest("hex"),
        overflow: false,
      });
    };
    const ask = async (question) => {
      if (!(await page.getByLabel("Pergunta", { exact: true }).isVisible()))
        await page.getByRole("button", { name: "Editar pergunta" }).click();
      await page
        .getByLabel("Interpretador", { exact: true })
        .selectOption("demo");
      const response = page.waitForResponse(
        (r) =>
          r.url().endsWith("/api/assistant/query") &&
          r.request().method() === "POST",
      );
      await page.getByLabel("Pergunta", { exact: true }).fill(question);
      await page.getByRole("button", { name: "Enviar pergunta" }).click();
      const result = await response;
      expect(result.status()).toBe(200);
      const answer = await result.json();
      expect(answer.mode).toBe("demo");
      await expect(page.getByTestId("answer").last()).toContainText(question);
      report.queries.push({
        question,
        mode: answer.mode,
        status: answer.status,
        result: answer.result,
      });
      return answer;
    };
    await page.goto(report.application);
    await page.getByRole("radio", { name: /Gerente · Aurora Casa/ }).check();
    await page.getByRole("button", { name: "Entrar" }).click();
    await expect(
      page.getByRole("heading", { name: "Análise de vendas" }),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Nova análise", exact: true })
      .click();
    await page
      .getByLabel("Interpretador", { exact: true })
      .selectOption("demo");
    await capture("inicio.png");
    await page.setViewportSize({ width: 390, height: 844 });
    await capture("inicio-mobile.png");
    await page.setViewportSize({ width: 1440, height: 1000 });
    const daily = await ask(
      "Mostre a evolução diária da receita nos últimos 7 dias",
    );
    expect(daily.status).toBe("ready");
    expect(daily.result.rows).toHaveLength(7);
    expect(daily.result.scope.map((store) => store.id)).toEqual(["a001"]);
    expect(
      daily.result.rows
        .reduce((sum, row) => sum + BigInt(row.revenue_cents), 0n)
        .toString(),
    ).toBe(daily.result.totals.revenue_cents);
    await expect(
      page.getByRole("img", { name: /^Evolução diária\./ }),
    ).toBeVisible();
    await capture("evolucao-diaria.png");
    const evidence = page.waitForResponse((r) =>
      r.url().endsWith(`/answers/${daily.id}/evidence`),
    );
    await page.getByText("Cálculo", { exact: true }).click();
    expect((await evidence).status()).toBe(200);
    await expect(
      page.getByText("Totais por dia", { exact: true }),
    ).toBeVisible();
    await capture("consulta-com-calculo.png");
    await page.getByText("Cálculo", { exact: true }).click();
    await page.setViewportSize({ width: 390, height: 844 });
    await capture("consulta-mobile.png");
    await page.setViewportSize({ width: 1440, height: 1000 });
    const unsupported = await ask("Quanto vendi ontem somente em dinheiro?");
    expect(unsupported.result).toBeNull();
    await capture("filtro-nao-suportado.png");
    expect(report.page_errors).toEqual([]);
    expect(report.rejected_requests).toEqual([]);
    fs.writeFileSync(
      path.join(output, "capture.json"),
      JSON.stringify(report, null, 2) + "\n",
    );
    console.log(JSON.stringify(report));
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
