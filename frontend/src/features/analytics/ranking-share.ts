import type { Result } from "@/lib/contracts";

export function rankingRevenueShare(result: Result): string | null {
  if (
    result.intent !== "ranking" ||
    result.metric !== "revenue" ||
    !result.totals
  )
    return null;
  const total = BigInt(result.totals.revenue_cents);
  if (total <= 0n) return null;
  const selected = result.rows.reduce(
    (sum, row) => sum + BigInt(row.revenue_cents),
    0n,
  );
  const hundredths = (selected * 10_000n + total / 2n) / total;
  return `${hundredths / 100n},${String(hundredths % 100n).padStart(2, "0")}`;
}
