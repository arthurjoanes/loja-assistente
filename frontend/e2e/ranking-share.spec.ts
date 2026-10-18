import { expect, test } from "@playwright/test";
import { rankingRevenueShare } from "../src/features/analytics/ranking-share";
import type { Result } from "../src/lib/contracts";

test("participação do ranking usa a receita total, não a soma do top", () => {
  const totals = {
    revenue_cents: "3",
    orders: 2,
    units: 2,
    average_ticket_cents: "2",
  };
  const result: Result = {
    intent: "ranking",
    metric: "revenue",
    scope: [{ id: "a001", name: "Centro" }],
    period: { start: "2026-08-10", end: "2026-08-17" },
    timezone: "America/Sao_Paulo",
    currency: "BRL",
    unit: "cents",
    formula: "sum(revenue_cents)",
    value: "3",
    rows: ["a", "b"].map((key) => ({
      ...totals,
      key,
      label: key,
      revenue_cents: "1",
    })),
    totals,
    coverage: {
      status: "complete",
      covered_days: 7,
      expected_days: 7,
      missing: [],
    },
    comparison: null,
    evidence: [],
    dataset_version: "test",
    request_id: "ranking-share",
  };
  expect(rankingRevenueShare(result)).toBe("66,67");
  expect(rankingRevenueShare({ ...result, metric: "orders" })).toBeNull();
  expect(
    rankingRevenueShare({ ...result, metric: "average_ticket" }),
  ).toBeNull();
  expect(
    rankingRevenueShare({
      ...result,
      totals: { ...totals, revenue_cents: "0" },
    }),
  ).toBeNull();
  expect(
    rankingRevenueShare({
      ...result,
      rows: [{ ...result.rows[0], revenue_cents: "9007199254740993" }],
      totals: { ...totals, revenue_cents: "18014398509481986" },
    }),
  ).toBe("50,00");
});
