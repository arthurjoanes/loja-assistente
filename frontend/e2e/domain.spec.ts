import { expect, test } from "@playwright/test";
import {
  validPeriod,
  selectPeriod,
} from "../src/features/assistant/period-selection";
import {
  analysisReducer,
  emptyAnalysis,
} from "../src/features/assistant/conversation-state";
import {
  MAX_REQUEST_BYTES,
  readRequestBody,
  RequestBodyTooLarge,
} from "../src/lib/server/request-body";
import { money } from "../src/lib/format";
import type { Answer, Row } from "../src/lib/contracts";
import { dailySeries } from "../src/features/analytics/daily-series";

for (const days of [1, 7, 30]) {
  test(`série de ${days} dias preserva zero, indisponível e valores exatos`, () => {
    const rows: Row[] = Array.from({ length: days }, (_, index) => ({
      key: `2026-07-${String(index + 1).padStart(2, "0")}`,
      label: `2026-07-${String(index + 1).padStart(2, "0")}`,
      revenue_cents: index === 0 ? "9007199254740993" : "0",
      orders: index === 0 ? 1 : 0,
      units: index === 0 ? 1 : 0,
      average_ticket_cents: index === 0 ? "9007199254740993" : null,
    }));
    const before = structuredClone(rows);
    const period = {
      start: "2026-07-01",
      end: `2026-07-${String(days + 1).padStart(2, "0")}`,
    };
    const revenue = dailySeries(rows, "revenue", period);
    expect(revenue.points.map(({ row }) => row?.key)).toEqual(
      rows.map((row) => row.key),
    );
    expect(revenue.points[0].height).toBe(100);
    expect(money(revenue.points[0].value)).toBe("R$ 90.071.992.547.409,93");
    expect(revenue.axisIndices[0]).toBe(0);
    expect(revenue.axisIndices.at(-1)).toBe(days - 1);
    expect(revenue.axisIndices.length).toBeLessThanOrEqual(3);
    for (const point of revenue.points.slice(1)) {
      expect(point.height).toBe(0);
      expect(point.value).toBe("0");
    }
    const ticket = dailySeries(rows, "average_ticket", period);
    expect(ticket.points.slice(1).every((point) => point.value === null)).toBe(
      true,
    );
    expect(
      dailySeries(
        rows.map((row) => ({ ...row, revenue_cents: "0" })),
        "revenue",
        period,
      ).points.every((point) => point.height === 0),
    ).toBe(true);
    expect(rows).toEqual(before);
    if (days > 1) {
      const incomplete = dailySeries(
        rows.filter((_, index) => index !== 1),
        "revenue",
        period,
      );
      expect(incomplete.points).toHaveLength(days);
      expect(incomplete.points[1]).toMatchObject({
        date: "2026-07-02",
        row: null,
        value: null,
        height: 0,
      });
      expect(incomplete.points[2].row?.key).toBe("2026-07-03");
    }
  });
}

for (const [start, end, valid] of [
  ["2026-08-16", "2026-08-17", true],
  ["2026-05-19", "2026-08-17", true],
  ["2026-05-18", "2026-08-17", false],
  ["2026-08-17", "2026-08-17", false],
  ["2026-08-18", "2026-08-17", false],
  ["", "2026-08-17", false],
  ["2026-08-16", "", false],
  ["0001-01-01", "0001-01-02", true],
  ["0000-01-01", "0000-01-02", false],
  ["9999-12-30", "9999-12-31", true],
  ["2026-02-29", "2026-03-01", false],
  ["2024-02-29", "2024-03-01", true],
] as const) {
  test(`intervalo puro ${start || "vazio"} / ${end || "vazio"}`, () => {
    expect(validPeriod({ start, end })).toBe(valid);
  });
}

test("preset personalizado preserva edição e pergunta remove filtro", () => {
  const current = { start: "2026-08-18", end: "2026-08-17" };
  expect(selectPeriod("custom", "2026-08-17", current)).toEqual(current);
  expect(selectPeriod("question", "2026-08-17", current)).toBeNull();
  expect(validPeriod(null)).toBe(true);
});

test("esclarecimento preserva filtros; troca de identidade limpa toda análise", () => {
  const previous = {
    ...emptyAnalysis(["a001"], "llm"),
    question: "Receita?",
    period: { start: "2026-08-15", end: "2026-08-16" },
    periodPreset: "custom",
  };
  const answer: Answer = {
    id: "answer",
    conversation_id: "conversation",
    question: "Receita?",
    status: "needs_clarification",
    message: "Informe um período.",
    mode: "llm",
    plan: null,
    result: null,
    request_id: "request",
    created_at: "2026-09-21T10:00:00Z",
  };
  const clarified = analysisReducer(previous, {
    type: "answer",
    value: answer,
  });
  expect(clarified.period).toEqual(previous.period);
  expect(clarified.periodPreset).toBe("custom");
  expect(clarified.storeIds).toEqual(["a001"]);
  expect(analysisReducer(clarified, { type: "reset" })).toEqual(
    emptyAnalysis(),
  );
  expect(previous.answers).toHaveLength(0);
});

for (const declared of [null, "1", "16385", "invalid"]) {
  test(`proxy conta bytes do stream com Content-Length ${declared}`, async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(new Uint8Array(8192));
        controller.enqueue(new Uint8Array(8193));
        controller.close();
      },
    });
    const request = new Request("http://localhost/api/auth/login", {
      method: "POST",
      body: stream,
      headers: declared ? { "Content-Length": declared } : {},
      ...{ duplex: "half" },
    });
    await expect(readRequestBody(request)).rejects.toBeInstanceOf(
      RequestBodyTooLarge,
    );
  });
}

test("proxy preserva 16 KiB e centavos grandes formatam sem Number", async () => {
  const request = new Request("http://localhost/api/auth/login", {
    method: "POST",
    body: "x".repeat(MAX_REQUEST_BYTES),
  });
  expect(new TextDecoder().decode(await readRequestBody(request))).toBe(
    "x".repeat(MAX_REQUEST_BYTES),
  );
  expect(money("9007199254740993")).toBe("R$ 90.071.992.547.409,93");
  expect(money("18446744073709553614")).toBe("R$ 184.467.440.737.095.536,14");
  expect(money("100.495")).toBe("R$ 1,00");
  expect(money("100.5")).toBe("R$ 1,01");
  expect(money(null)).toBe("Indisponível");
});
