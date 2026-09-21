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
import type { Answer } from "../src/lib/contracts";

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
