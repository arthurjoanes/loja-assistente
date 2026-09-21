import { test, expect, type Page } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import type { Answer } from "../src/lib/contracts";
import { money } from "../src/lib/format";

async function enter(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(
    page.getByRole("heading", { name: "Análise de vendas" }),
  ).toBeVisible();
}
async function query(page: Page, question: string): Promise<Answer> {
  const response = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/assistant/query") &&
      response.request().method() === "POST",
  );
  await page.getByLabel("Pergunta", { exact: true }).fill(question);
  await page.getByRole("button", { name: "Enviar pergunta" }).click();
  const result = await response;
  expect(result.status()).toBe(200);
  const answer: Answer = await result.json();
  await expect(page.getByTestId("answer").last()).toContainText(question);
  return answer;
}
async function settleLayout(page: Page) {
  await page.evaluate(
    () =>
      new Promise<void>((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(() => resolve())),
      ),
  );
}

test("histórico tardio não apaga a conversa recém-criada", async ({ page }) => {
  let release = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let captured = () => {};
  const snapshotReady = new Promise<void>((resolve) => {
    captured = resolve;
  });
  let delivered = () => {};
  const snapshotDelivered = new Promise<void>((resolve) => {
    delivered = resolve;
  });
  let holdFirst = true;
  await page.route("**/api/conversations", async (route) => {
    if (route.request().method() === "GET" && holdFirst) {
      holdFirst = false;
      const response = await route.fetch();
      captured();
      await held;
      await route.fulfill({ response });
      delivered();
    } else await route.continue();
  });
  await enter(page);
  await snapshotReady;
  try {
    await query(page, "Quanto vendi em 2026-08-15?");
    const selected = page
      .getByRole("navigation", { name: "Histórico pessoal" })
      .locator('button[aria-current="page"]');
    await expect(selected).toContainText("Quanto vendi em 2026-08-15?");
    const selectedTime = await selected
      .locator("time")
      .getAttribute("datetime");
    release();
    await snapshotDelivered;
    await settleLayout(page);
    await expect(selected).toContainText("Quanto vendi em 2026-08-15?");
    await expect(selected.locator("time")).toHaveAttribute(
      "datetime",
      selectedTime!,
    );
  } finally {
    release();
  }
});

test("histórico distingue horários, revela título longo e drawer devolve foco", async ({
  page,
}) => {
  await enter(page);
  const question =
    "Mostre a evolução diária da receita nos últimos 7 dias para conferir os dias com vendas e os dias cobertos sem vendas na loja Centro.";
  const answer = await query(page, question);
  const persisted = await (
    await page.request.get("/api/conversations/" + answer.conversation_id)
  ).json();
  const selected = page
    .getByRole("navigation", { name: "Histórico pessoal" })
    .locator('button[aria-current="page"]');
  await selected.focus();
  await expect(selected.locator("time")).toBeVisible();
  expect(await selected.locator("time").getAttribute("datetime")).toBeTruthy();
  expect(persisted.title.length).toBeGreaterThan(80);
  expect(await selected.getAttribute("title")).toBe(persisted.title);
  const titleIsExpanded = await selected
    .locator(".history-title")
    .evaluate((element) => element.scrollHeight <= element.clientHeight + 1);
  expect(titleIsExpanded).toBe(true);

  await page.setViewportSize({ width: 390, height: 844 });
  const opener = page.getByRole("button", { name: "Abrir menu" });
  await opener.focus();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Loja", { exact: true })).toBeFocused();
  await opener.click();
  const dialog = page.getByRole("dialog", { name: "Navegação principal" });
  await expect(dialog).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Fechar menu", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(page.getByRole("button", { name: "Sair" })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("button", { name: "Fechar menu", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(opener).toBeFocused();
});

test("evidência, foco, alvos e refluxo permanecem acessíveis em seis geometrias", async ({
  page,
}, testInfo) => {
  await enter(page);
  const answer = await query(
    page,
    "Mostre a evolução diária da receita nos últimos 7 dias",
  );
  const chartControls = await page
    .getByRole("button", { name: /^(Gráfico|Tabela)$/ })
    .evaluateAll((controls) =>
      controls.map((control) => ({
        name: control.textContent?.trim(),
        width: control.getBoundingClientRect().width,
        height: control.getBoundingClientRect().height,
      })),
    );
  const response = page.waitForResponse((response) =>
    response.url().endsWith("/answers/" + answer.id + "/evidence"),
  );
  await page.getByText("Cálculo", { exact: true }).click();
  expect((await response).status()).toBe(200);
  const end = page.locator(".request-id").last();
  await expect(end).toContainText(answer.request_id);

  const sizes = [
    { width: 1440, height: 900, name: "1440x900" },
    { width: 1366, height: 768, name: "1366x768" },
    { width: 768, height: 1024, name: "768x1024" },
    { width: 390, height: 844, name: "390x844" },
    { width: 320, height: 844, name: "320x844" },
    { width: 320, height: 256, name: "320x256-zoom-equivalent" },
  ];
  const checks = [];
  for (const size of sizes) {
    await page.setViewportSize({ width: size.width, height: size.height });
    await end.evaluate((element) =>
      element.scrollIntoView({ block: "end", behavior: "instant" }),
    );
    await settleLayout(page);
    const layout = await page.evaluate(() => {
      const main = document.querySelector<HTMLElement>(".conversation-scroll")!;
      const end = document.querySelector<HTMLElement>(".request-id")!;
      const composer = document.querySelector<HTMLElement>(
        ".composer-container",
      )!;
      const rect = (element: Element) => {
        const value = element.getBoundingClientRect();
        return {
          x: value.x,
          y: value.y,
          width: value.width,
          height: value.height,
          bottom: value.bottom,
          right: value.right,
        };
      };
      const endRect = rect(end);
      const mainRect = rect(main);
      const composerRect = rect(composer);
      const centerX = Math.min(
        innerWidth - 2,
        Math.max(2, endRect.x + endRect.width / 2),
      );
      const centerY = endRect.y + endRect.height / 2;
      const hit = document.elementFromPoint(centerX, centerY);
      const endReached =
        endRect.y >= 0 &&
        endRect.bottom <= innerHeight + 1 &&
        (hit === end || end.contains(hit));
      const controls = Array.from(
        document.querySelectorAll<HTMLElement>(
          "button:not(:disabled), select:not(:disabled), input:not(:disabled), textarea:not(:disabled), summary",
        ),
      );
      const targets = controls.flatMap((control) => {
        const bounds = rect(control);
        if (
          bounds.width === 0 ||
          bounds.height === 0 ||
          getComputedStyle(control).visibility === "hidden"
        )
          return [];
        const cx = bounds.x + bounds.width / 2;
        const cy = bounds.y + bounds.height / 2;
        if (cx < 0 || cy < 0 || cx > innerWidth || cy > innerHeight) return [];
        const top = document.elementFromPoint(cx, cy);
        if (top !== control && !control.contains(top)) return [];
        return [
          {
            name: (
              control.getAttribute("aria-label") ||
              control.textContent ||
              control.tagName
            )
              .trim()
              .slice(0, 80),
            width: bounds.width,
            height: bounds.height,
          },
        ];
      });
      return {
        viewport: {
          width: innerWidth,
          height: innerHeight,
          deviceScaleFactor: devicePixelRatio,
        },
        pageWidth: document.documentElement.scrollWidth,
        horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
        scrollMode: getComputedStyle(main).overflowY,
        main: mainRect,
        evidenceEnd: endRect,
        composer: composerRect,
        evidenceEndReached: endReached,
        evidenceClearOfComposer: endRect.bottom <= composerRect.y + 1,
        targets,
        smallTargets: targets.filter(
          (target) => target.width < 24 || target.height < 24,
        ),
      };
    });
    // Walk backwards from the composer into the last keyboard stop of the evidence.
    await page.getByLabel("Pergunta", { exact: true }).focus();
    await page.keyboard.press("Shift+Tab");
    await page.keyboard.press("Shift+Tab");
    await settleLayout(page);
    const keyboard = await page.evaluate(() => {
      const active = document.activeElement as HTMLElement;
      const rect = active.getBoundingClientRect();
      const x = Math.min(innerWidth - 2, Math.max(2, rect.x + rect.width / 2));
      const y = Math.min(
        innerHeight - 2,
        Math.max(2, rect.y + rect.height / 2),
      );
      const hit = document.elementFromPoint(x, y);
      const composer = document
        .querySelector<HTMLElement>(".composer-container")!
        .getBoundingClientRect();
      return {
        role: active.getAttribute("role"),
        label: active.getAttribute("aria-label"),
        insideEvidence: Boolean(active.closest(".evidence")),
        visibleHeight: Math.max(
          0,
          Math.min(rect.bottom, innerHeight, composer.y) -
            Math.max(rect.top, 0),
        ),
        uncovered: hit === active || active.contains(hit),
        focusOutline: getComputedStyle(active).outlineStyle,
      };
    });
    await end.evaluate((element) =>
      element.scrollIntoView({ block: "end", behavior: "instant" }),
    );
    await settleLayout(page);
    const baseline = Boolean(process.env.LAYOUT_BASELINE);
    const screenshotDir = process.env.SCREENSHOT_DIR;
    const screenshotPath = screenshotDir
      ? screenshotDir +
        (baseline ? "/before-quality/measure-" : "/quality-") +
        size.name +
        ".png"
      : testInfo.outputPath(size.name + ".png");
    await page.screenshot({ path: screenshotPath });
    await page.getByLabel("Pergunta", { exact: true }).focus();
    await settleLayout(page);
    const input = await page
      .getByLabel("Pergunta", { exact: true })
      .evaluate((element) => {
        const rect = element.getBoundingClientRect();
        const hit = document.elementFromPoint(
          rect.x + rect.width / 2,
          rect.y + rect.height / 2,
        );
        return {
          visible: rect.top >= 0 && rect.bottom <= innerHeight,
          uncovered: hit === element,
          focused: document.activeElement === element,
        };
      });
    if (size.height === 256 && screenshotDir && !baseline) {
      await page.screenshot({
        path: screenshotDir + "/quality-lowheight-composer.png",
      });
    }
    checks.push({ name: size.name, ...layout, keyboard, input });
  }
  const report = {
    capturedAt: new Date().toISOString(),
    mode: process.env.LAYOUT_BASELINE ? "baseline-inspection" : "verification",
    scenario:
      "Consulta diária real, evidência real aberta e navegação por teclado.",
    zoomMethod:
      "320×256 CSS px reproduz a geometria de 1280×1024 em 400%; zoom nativo da interface do navegador não foi medido.",
    chartControls,
    checks,
  };
  mkdirSync("test-results", { recursive: true });
  writeFileSync(
    "test-results/" +
      (process.env.LAYOUT_BASELINE
        ? "viewport-baseline.json"
        : "viewport-checks.json"),
    JSON.stringify(report, null, 2),
  );
  if (!process.env.LAYOUT_BASELINE && process.env.SCREENSHOT_DIR) {
    writeFileSync(
      process.env.SCREENSHOT_DIR + "/viewport-checks.json",
      JSON.stringify(report, null, 2),
    );
  }
  await testInfo.attach("viewport-checks", {
    body: JSON.stringify(report, null, 2),
    contentType: "application/json",
  });
  if (!process.env.LAYOUT_BASELINE) {
    for (const control of chartControls) {
      expect(
        control.height,
        control.name + ": altura do alvo",
      ).toBeGreaterThanOrEqual(24);
      expect(
        control.width,
        control.name + ": largura do alvo",
      ).toBeGreaterThanOrEqual(24);
    }
    for (const check of checks) {
      expect
        .soft(check.horizontalOverflow, check.name + ": overflow horizontal")
        .toBe(false);
      expect
        .soft(
          check.evidenceEndReached,
          check.name + ": fim da evidência acessível",
        )
        .toBe(true);
      expect
        .soft(
          check.evidenceClearOfComposer,
          check.name + ": evidência fora do compositor",
        )
        .toBe(true);
      expect
        .soft(check.smallTargets, check.name + ": alvos menores que 24px")
        .toEqual([]);
      expect
        .soft(
          check.keyboard.insideEvidence,
          check.name + ": foco volta à evidência",
        )
        .toBe(true);
      expect
        .soft(
          check.keyboard.visibleHeight,
          check.name + ": área visível do controle",
        )
        .toBeGreaterThan(24);
      expect
        .soft(check.keyboard.uncovered, check.name + ": foco não encoberto")
        .toBe(true);
      expect
        .soft(check.keyboard.focusOutline, check.name + ": foco visível")
        .not.toBe("none");
      expect
        .soft(check.input, check.name + ": campo acessível após rolagem e foco")
        .toEqual({
          visible: true,
          uncovered: true,
          focused: true,
        });
    }
  }
});

test("zero coberto, receita de 90 dias e cobertura parcial preservam o significado dos números", async ({
  page,
}) => {
  await enter(page);
  const zero = await query(page, "Qual foi a receita em 2026-08-11?");
  expect(zero.result?.coverage.status).toBe("complete");
  expect(zero.result?.totals).toEqual({
    revenue_cents: "0",
    orders: 0,
    units: 0,
    average_ticket_cents: null,
  });
  await expect(page.getByTestId("answer").last()).toContainText("R$ 0,00");
  await expect(page.getByTestId("answer").last()).toContainText("Indisponível");

  const large = await query(page, "Qual foi a receita nos últimos 90 dias?");
  expect(large.result?.coverage.status).toBe("complete");
  expect(large.result?.coverage.covered_days).toBe(90);
  expect(BigInt(large.result!.totals!.revenue_cents)).toBeGreaterThan(
    10_000_000n,
  );
  await page.setViewportSize({ width: 320, height: 844 });
  const primary = page
    .getByTestId("answer")
    .last()
    .locator(".primary-metric dd");
  await expect(primary).toHaveText(money(large.result!.totals!.revenue_cents));
  expect(
    await primary.evaluate(
      (element) => element.scrollWidth <= element.clientWidth,
    ),
  ).toBe(true);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);

  const partial = await query(
    page,
    "Qual foi a receita de 2026-05-18 a 2026-05-20?",
  );
  expect(partial.result?.coverage).toEqual({
    status: "partial",
    covered_days: 2,
    expected_days: 3,
    missing: [{ store_id: "a001", date: "2026-05-18" }],
  });
  const card = page.getByTestId("answer").last();
  await expect(card).toContainText(
    "Apenas 2 de 3 combinações de loja e dia carregadas",
  );
  await expect(card).toContainText("Totais parciais.");
  const evidence = page.waitForResponse((response) =>
    response.url().endsWith("/answers/" + partial.id + "/evidence"),
  );
  await card.getByText("Cálculo", { exact: true }).click();
  expect((await evidence).status()).toBe(200);
  await card.getByText("Ver 1 combinações ausentes", { exact: true }).click();
  await expect(
    card.getByText("a001 · 18/05/2026", { exact: true }),
  ).toBeVisible();
});

test("preferência de movimento reduzido evita rolagem animada da conversa", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => {
    const original = Element.prototype.scrollIntoView;
    const behaviors: string[] = [];
    Object.assign(window, { conversationScrollBehaviors: behaviors });
    Element.prototype.scrollIntoView = function (options) {
      if (
        this.parentElement?.classList.contains("conversation-thread") &&
        typeof options === "object"
      ) {
        behaviors.push(options.behavior ?? "auto");
      }
      original.call(this, options);
    };
  });
  await enter(page);
  await query(page, "Quanto vendi ontem?");
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          (Reflect.get(window, "conversationScrollBehaviors") as string[])
            .length,
      ),
    )
    .toBeGreaterThan(0);
  const behaviors = await page.evaluate(
    () => Reflect.get(window, "conversationScrollBehaviors") as string[],
  );
  expect(behaviors.length).toBeGreaterThan(0);
  expect(behaviors).not.toContain("smooth");
});
