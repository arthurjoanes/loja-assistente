/* Capture the running synthetic Demo through its real browser/API contracts.
 * No source writes, pixel editing, screenshot CSS, or paid-provider calls.
 * Run with Node from the existing Playwright image; dependencies are resolved
 * from /app/node_modules or the repository's existing frontend/node_modules.
 */
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");
const dependencyRoot = fs.existsSync("/app/package.json")
  ? "/app/package.json"
  : path.join(__dirname, "../frontend/package.json");
const dependency = createRequire(dependencyRoot);
const { chromium, firefox, webkit, expect } = dependency("@playwright/test");
const AxeBuilder = dependency("@axe-core/playwright").default;

const output = process.env.UIUX_OUTPUT_DIR;
const baseURL = process.env.BASE_URL || process.env.E2E_BASE_URL;
const stage = process.env.STAGE || "inspection";
const engine = process.env.UIUX_BROWSER || "chromium";
if (!output || !baseURL)
  throw new Error("UIUX_OUTPUT_DIR and BASE_URL are required");
if (!/^[a-z0-9-]+$/i.test(stage))
  throw new Error("STAGE must be a simple label");
const widths = (process.env.UIUX_WIDTHS || "320,390,768,1024,1440")
  .split(",")
  .map(Number);
if (widths.some((value) => !Number.isInteger(value) || value < 240))
  throw new Error("Invalid UIUX_WIDTHS");
fs.mkdirSync(output, { recursive: true });
const report = {
  version: 2,
  stage,
  browser: engine,
  started_at_utc: new Date().toISOString(),
  execution:
    "real application; synthetic-v1 Demo; no intercepted API responses",
  profile: "Gerente · Aurora Casa",
  reference_date: "2026-08-17",
  paid_calls: 0,
  screenshot_method:
    "viewport screenshots; document and all scrolled containers reset naturally and stable at zero for three animation frames before top captures; keyboard focus captures use natural focus scrolling; no CSS injection or pixel editing",
  native_zoom: "not verified",
  screen_reader: "not verified",
  mobile_emulation:
    "Chromium at 320/390 CSS px: isMobile and touch enabled, device scale factor 1. Firefox/WebKit: touch and narrow viewport, without mobile-layout emulation. These are browser emulations, not physical-device or native-zoom tests.",
  states: [],
  journeys: [],
  telemetry: [],
};
function save() {
  fs.writeFileSync(
    path.join(output, `${stage}-${engine}-report.json`),
    JSON.stringify(report, null, 2) + "\n",
  );
}
function safeURL(value) {
  const url = new URL(value);
  return `${url.origin}${url.pathname}`;
}
function pngDimensions(filename) {
  const bytes = fs.readFileSync(path.join(output, filename));
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
}
async function settle(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(resolve)),
    );
  });
}
async function resetViewportTop(page) {
  await settle(page);
  return page.evaluate(async () => {
    const containers = () =>
      [...document.querySelectorAll("*")]
        .filter((element) => element instanceof HTMLElement)
        .filter(
          (element) =>
            element.scrollTop !== 0 ||
            element.scrollLeft !== 0 ||
            element.scrollHeight > element.clientHeight + 1 ||
            element.scrollWidth > element.clientWidth + 1,
        );
    const describe = (element) => ({
      tag: element.tagName,
      id: element.id,
      class: element.className,
      x: element.scrollLeft,
      y: element.scrollTop,
      client_width: element.clientWidth,
      client_height: element.clientHeight,
      scroll_width: element.scrollWidth,
      scroll_height: element.scrollHeight,
    });
    const before = containers().map(describe);
    if (document.activeElement instanceof HTMLElement)
      document.activeElement.blur();
    let stable = 0;
    let frames = 0;
    let resets = 0;
    while (stable < 3 && frames < 120) {
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
      for (const element of containers()) {
        if (element.scrollTop !== 0 || element.scrollLeft !== 0) {
          element.scrollTo({ top: 0, left: 0, behavior: "instant" });
          resets += 1;
        }
      }
      await new Promise((resolve) => requestAnimationFrame(resolve));
      frames += 1;
      const atTop =
        scrollX === 0 &&
        scrollY === 0 &&
        containers().every(
          (element) => element.scrollTop === 0 && element.scrollLeft === 0,
        );
      stable = atTop ? stable + 1 : 0;
    }
    if (stable < 3)
      throw new Error("Viewport/container scroll did not settle at zero");
    return {
      before,
      after: containers().map(describe),
      stable_frames: stable,
      sampled_frames: frames,
      container_resets: resets,
    };
  });
}
async function navigation(page, name) {
  const opener = page.getByRole("button", { name: "Abrir menu", exact: true });
  if (await opener.isVisible()) await opener.click();
  await page.getByRole("button", { name, exact: true }).click();
}
async function editor(page) {
  if (!(await page.getByLabel("Pergunta", { exact: true }).isVisible()))
    await page
      .getByRole("button", { name: "Editar pergunta", exact: true })
      .click();
}
async function ask(page, question) {
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
  const answer = await reply.json();
  await expect(page.getByTestId("answer").last()).toContainText(question);
  await expect(page.getByLabel("Pergunta", { exact: true })).toBeEnabled();
  return answer;
}
async function metrics(page) {
  return page.evaluate(() => {
    const visible = (element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        style.visibility !== "hidden" &&
        style.display !== "none"
      );
    };
    const label = (element) =>
      (
        element.getAttribute("aria-label") ||
        element.textContent ||
        element.getAttribute("name") ||
        element.tagName
      )
        .trim()
        .slice(0, 100);
    const controls = [
      ...document.querySelectorAll(
        "button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),summary",
      ),
    ]
      .filter(visible)
      .flatMap((element) => {
        const rect = element.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) return [];
        const hit = document.elementFromPoint(x, y);
        if (hit !== element && !element.contains(hit)) return [];
        // A native radio is operated through its wrapping label's hit target.
        const target = element.matches(
          'input[type="radio"],input[type="checkbox"]',
        )
          ? element.closest("label") || element
          : element;
        const bounds = target.getBoundingClientRect();
        return [
          { name: label(target), width: bounds.width, height: bounds.height },
        ];
      });
    const active = document.activeElement;
    const rect = active?.getBoundingClientRect();
    const hit = rect
      ? document.elementFromPoint(
          Math.max(1, Math.min(innerWidth - 1, rect.x + rect.width / 2)),
          Math.max(1, Math.min(innerHeight - 1, rect.y + rect.height / 2)),
        )
      : null;
    const fontElements = [
      ...document.querySelectorAll("h1,h2,h3,p,button,textarea"),
    ].filter(visible);
    return {
      viewport: {
        width: innerWidth,
        height: innerHeight,
        device_pixel_ratio: devicePixelRatio,
      },
      scroll: { x: scrollX, y: scrollY },
      scroll_containers: [...document.querySelectorAll("*")]
        .filter((element) => element instanceof HTMLElement)
        .filter(
          (element) =>
            element.scrollTop !== 0 ||
            element.scrollLeft !== 0 ||
            element.scrollHeight > element.clientHeight + 1 ||
            element.scrollWidth > element.clientWidth + 1,
        )
        .map((element) => ({
          tag: element.tagName,
          id: element.id,
          class: element.className,
          x: element.scrollLeft,
          y: element.scrollTop,
          client_width: element.clientWidth,
          client_height: element.clientHeight,
          scroll_width: element.scrollWidth,
          scroll_height: element.scrollHeight,
        })),
      header_top:
        document.querySelector("header")?.getBoundingClientRect().top ?? null,
      horizontal_overflow:
        document.documentElement.scrollWidth > innerWidth + 1,
      document_width: document.documentElement.scrollWidth,
      small_targets: controls.filter(
        (control) => control.width < 24 || control.height < 24,
      ),
      controls,
      focus: {
        name: active ? label(active) : null,
        tag: active?.tagName,
        outline: active ? getComputedStyle(active).outlineStyle : null,
        visible: Boolean(rect && rect.top >= 0 && rect.bottom <= innerHeight),
        uncovered: Boolean(active && (hit === active || active.contains(hit))),
      },
      fonts: {
        status: document.fonts.status,
        families: [
          ...new Set(
            fontElements.map((element) => getComputedStyle(element).fontFamily),
          ),
        ],
      },
      links: [...document.querySelectorAll("a[href]")].map((element) => ({
        text: label(element),
        href: element.getAttribute("href"),
        local_target_exists:
          !element.getAttribute("href").startsWith("#") ||
          Boolean(
            document.getElementById(element.getAttribute("href").slice(1)),
          ),
      })),
      reduced_motion: matchMedia("(prefers-reduced-motion: reduce)").matches,
    };
  });
}
async function capture(page, state, width, initial, expected, focusTarget) {
  const topReset = await resetViewportTop(page);
  const filename = `${stage}-${engine}-${state}-${width}.png`;
  await page.screenshot({
    path: path.join(output, filename),
    fullPage: false,
    animations: "disabled",
  });
  const scan = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .analyze();
  const axeFile = `${stage}-${engine}-${state}-${width}-axe.json`;
  fs.writeFileSync(
    path.join(output, axeFile),
    JSON.stringify(scan, null, 2) + "\n",
  );
  const record = {
    state,
    width,
    height: 900,
    route: new URL(page.url()).pathname,
    initial,
    expected,
    top_reset: topReset,
    screenshot: filename,
    png_dimensions: pngDimensions(filename),
    axe: axeFile,
    captured_at_utc: new Date().toISOString(),
    axe_summary: {
      violations: scan.violations.map((item) => ({
        id: item.id,
        impact: item.impact,
        nodes: item.nodes.map((node) => node.target),
      })),
      incomplete: scan.incomplete.map((item) => ({
        id: item.id,
        nodes: item.nodes.map((node) => node.target),
      })),
      passes: scan.passes.length,
    },
    metrics: await metrics(page),
  };
  if (focusTarget) {
    await focusTarget.focus();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Shift+Tab");
    await settle(page);
    const focusFile = `${stage}-${engine}-${state}-${width}-focus.png`;
    await page.screenshot({
      path: path.join(output, focusFile),
      fullPage: false,
      animations: "disabled",
    });
    record.focus_screenshot = focusFile;
    record.focus_png_dimensions = pngDimensions(focusFile);
    record.focus_metrics = await metrics(page);
  }
  report.states.push(record);
  save();
}
async function removeFavorite(page, favorite) {
  const me = await page.request.get("/api/auth/me");
  if (!me.ok()) return;
  const current = await page.request.get(`/api/favorites/${favorite.id}`);
  if (!current.ok()) return;
  const session = await me.json();
  const value = await current.json();
  const reply = await page.request.post(
    `/api/favorites/${favorite.id}/delete`,
    {
      data: { revision: value.revision },
      headers: {
        Origin: new URL(page.url()).origin,
        "X-CSRF-Token": session.csrf_token,
      },
    },
  );
  expect(reply.status()).toBe(204);
}
async function journey(browser, width) {
  const context = await browser.newContext({
    baseURL,
    viewport: { width, height: 900 },
    deviceScaleFactor: 1,
    hasTouch: width <= 390,
    ...(engine === "chromium" ? { isMobile: width <= 390 } : {}),
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  let authenticated = false;
  const telemetry = {
    width,
    context: {
      css_width: width,
      css_height: 900,
      device_scale_factor: 1,
      has_touch: width <= 390,
      is_mobile: engine === "chromium" ? width <= 390 : false,
      mode:
        width > 390
          ? "desktop viewport"
          : engine === "chromium"
            ? "mobile browser emulation"
            : "narrow desktop viewport with touch; mobile layout emulation not used",
    },
    console_errors: [],
    console_error_details: [],
    page_errors: [],
    request_failures: [],
    http_errors: [],
    assets: [],
  };
  page.on("console", (message) => {
    if (message.type() === "error") {
      telemetry.console_errors.push(message.text());
      const location = message.location();
      const url = location.url ? safeURL(location.url) : null;
      const anonymousCheck =
        !authenticated &&
        url?.endsWith("/api/auth/me") &&
        /401/.test(message.text());
      telemetry.console_error_details.push({
        text: message.text(),
        url,
        classification: anonymousCheck
          ? "expected anonymous session check before login"
          : "unclassified console error; inspect alongside HTTP responses",
      });
    }
  });
  page.on("pageerror", (error) => telemetry.page_errors.push(error.message));
  page.on("requestfailed", (request) =>
    telemetry.request_failures.push({
      method: request.method(),
      url: safeURL(request.url()),
      error: request.failure()?.errorText,
    }),
  );
  page.on("response", (response) => {
    const request = response.request();
    if (response.status() >= 400)
      telemetry.http_errors.push({
        method: request.method(),
        url: safeURL(response.url()),
        status: response.status(),
        classification:
          request.method() === "GET" &&
          !authenticated &&
          response.status() === 401 &&
          new URL(response.url()).pathname === "/api/auth/me"
            ? "expected anonymous session check before login"
            : "unexpected HTTP error",
      });
    if (
      ["stylesheet", "script", "font", "image"].includes(request.resourceType())
    )
      telemetry.assets.push({
        type: request.resourceType(),
        url: safeURL(response.url()),
        status: response.status(),
      });
  });
  let favorite;
  try {
    await page.goto("/");
    await page.getByRole("radio", { name: /Gerente · Aurora Casa/ }).check();
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Análise de vendas", exact: true }),
    ).toBeVisible();
    authenticated = true;
    const me = await (await page.request.get("/api/auth/me")).json();
    expect(me.reference_date).toBe(report.reference_date);
    expect(me.dataset_version).toBe("synthetic-v1");
    expect(me.llm_available).toBe(false);
    await navigation(page, "Nova análise");
    await page.getByLabel("Loja", { exact: true }).selectOption("a001");
    await page.getByLabel("Período", { exact: true }).selectOption("question");
    await capture(
      page,
      "inicio",
      width,
      "New empty analysis; Centro; period defined by question; Demo",
      "Question and quick actions available without submitting",
      page.getByLabel("Pergunta", { exact: true }),
    );

    const pendingAnswer = await ask(page, "Receita da loja Centro");
    expect(pendingAnswer.status).toBe("needs_clarification");
    expect(pendingAnswer.pending_clarification.missing_field).toBe("period");
    expect(pendingAnswer.pending_clarification.partial_plan.store_ids).toEqual([
      "a001",
    ]);
    expect(pendingAnswer.pending_clarification.partial_plan.metric).toBe(
      "revenue",
    );
    const radio = page.getByRole("radio", { name: /^Ontem/i });
    if (width === 390) {
      const collapse = page.getByRole("button", {
        name: "Recolher próxima consulta",
        exact: true,
      });
      if (await collapse.isVisible()) {
        await collapse.click();
        const topReset = await resetViewportTop(page);
        const probe = {
          state: "pending-after-editor-collapse",
          width,
          radio_visible: await radio.isVisible(),
          confirm_visible: await page
            .getByRole("button", { name: "Confirmar escolha", exact: true })
            .isVisible(),
          top_reset: topReset,
          screenshot: `${stage}-${engine}-pending-collapsed-${width}.png`,
          metrics: await metrics(page),
        };
        await page.screenshot({
          path: path.join(output, probe.screenshot),
          fullPage: false,
          animations: "disabled",
        });
        probe.png_dimensions = pngDimensions(probe.screenshot);
        report.journeys.push(probe);
        await page
          .getByRole("button", { name: "Editar pergunta", exact: true })
          .click();
      }
    }
    await radio.check();
    await expect(page.getByLabel("Escopo a confirmar")).toContainText(
      "Centro (a001)",
    );
    await expect(page.getByLabel("Escopo a confirmar")).toContainText(
      "16/08/2026",
    );
    await capture(
      page,
      "pendente",
      width,
      "Revenue for Centro with no period; yesterday selected, not submitted",
      "Preview preserves revenue and Centro, with 16/08 included–17/08 excluded",
      radio,
    );
    await page
      .getByRole("button", { name: "Cancelar esclarecimento", exact: true })
      .click();

    await navigation(page, "Nova análise");
    await page.getByLabel("Loja", { exact: true }).selectOption("a001");
    const result = await ask(
      page,
      "Mostre a evolução diária da receita nos últimos 7 dias da loja Centro",
    );
    expect(result.result.intent).toBe("daily");
    expect(result.result.period).toEqual({
      start: "2026-08-10",
      end: "2026-08-17",
    });
    const evidenceResponse = page.waitForResponse((reply) =>
      reply.url().endsWith(`/answers/${result.id}/evidence`),
    );
    const disclosure = page.locator(".evidence > summary").last();
    await disclosure.click();
    expect((await evidenceResponse).status()).toBe(200);
    await expect(page.locator(".request-id").last()).toContainText(
      result.request_id,
    );
    await capture(
      page,
      "resultado",
      width,
      "Seven-day Centro revenue; server calculation expanded",
      "Exact totals, applied scope, day coverage and calculation remain readable",
      disclosure,
    );

    await page
      .getByRole("button", { name: "Salvar consulta favorita", exact: true })
      .click();
    await page
      .getByLabel("Nome da consulta favorita")
      .fill("Receita semanal · Centro");
    const favoriteResponse = page.waitForResponse(
      (reply) =>
        reply.url().endsWith("/api/favorites") &&
        reply.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Salvar favorito", exact: true })
      .click();
    const reply = await favoriteResponse;
    expect(reply.status()).toBe(200);
    favorite = await reply.json();
    await navigation(page, "Favoritos");
    const card = page.getByTestId("favorite").filter({
      has: page.getByRole("heading", { name: favorite.name, exact: true }),
    });
    await expect(card).toBeVisible();
    await expect(card).toContainText("10/08/2026");
    await capture(
      page,
      "favorito",
      width,
      "Personal saved seven-day Centro plan with fixed dates",
      "Open recorded calculation and execute again are distinct actions",
      card.getByRole("button", { name: "Executar novamente", exact: true }),
    );

    await navigation(page, "Nova análise");
    await page.getByLabel("Loja", { exact: true }).selectOption("a001");
    const absent = await ask(
      page,
      "Quanto vendi em 2025-01-01 na loja Centro?",
    );
    expect(absent.result.coverage.status).toBe("absent");
    expect(absent.result.totals).toBeNull();
    await expect(page.getByTestId("answer").last()).toContainText(
      "Sem dados carregados",
    );
    await capture(
      page,
      "sem-dados",
      width,
      "Centro on 01/01/2025, outside the synthetic coverage",
      "No numerical total substitutes missing data",
      page.getByRole("button", { name: "Editar pergunta", exact: true }),
    );
    report.journeys.push({
      width,
      pending: {
        metric: pendingAnswer.pending_clarification.partial_plan.metric,
        stores: pendingAnswer.pending_clarification.partial_plan.store_ids,
      },
      result: {
        plan: result.plan,
        coverage: result.result.coverage.status,
        totals: result.result.totals,
        rows: result.result.rows.length,
      },
      favorite: { name: favorite.name, plan: favorite.plan },
      absent: {
        status: absent.status,
        coverage: absent.result.coverage.status,
        totals: absent.result.totals,
      },
    });
  } finally {
    if (favorite) await removeFavorite(page, favorite);
    report.telemetry.push(telemetry);
    await context.close();
    save();
  }
}
(async () => {
  let browser;
  try {
    const browserType = { chromium, firefox, webkit }[engine];
    if (!browserType) throw new Error("Unsupported UIUX_BROWSER");
    browser = await browserType.launch({ headless: true });
    report.browser_version = browser.version();
    for (const width of widths) await journey(browser, width);
    report.status = "captured";
    console.log(
      `Captured ${report.states.length} real Demo states in ${engine}; report ${stage}-${engine}-report.json`,
    );
  } catch (error) {
    report.status = "failed";
    report.error = error.message;
    console.error(error.message);
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    report.finished_at_utc = new Date().toISOString();
    save();
  }
})();
