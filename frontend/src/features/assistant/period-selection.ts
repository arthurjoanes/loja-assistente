import type { Period } from "@/lib/contracts";
import { shiftDate } from "@/lib/format";

export function includedEnd(exclusive: string): string {
  return /^\d{4}-\d{2}-\d{2}$/.test(exclusive) &&
    Number.isFinite(Date.parse(exclusive))
    ? shiftDate(exclusive, -1)
    : "";
}

export function exclusiveEnd(included: string): string {
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(included) ||
    included > "9999-12-30" ||
    !Number.isFinite(Date.parse(included))
  )
    return "";
  return shiftDate(included, 1);
}

export function validPeriod(period: Period | null): boolean {
  if (period === null) return true;
  for (const value of [period.start, period.end]) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.startsWith("0000"))
      return false;
    const timestamp = Date.parse(value + "T12:00:00Z");
    if (
      !Number.isFinite(timestamp) ||
      new Date(timestamp).toISOString().slice(0, 10) !== value
    )
      return false;
  }
  const days = (Date.parse(period.end) - Date.parse(period.start)) / 86_400_000;
  return days >= 1 && days <= 90;
}

export function selectPeriod(
  preset: string,
  reference: string,
  current: Period | null,
): Period | null {
  if (preset === "question") return null;
  if (preset === "custom" && current) return current;
  const days = preset === "yesterday" ? 1 : preset === "week" ? 7 : 30;
  return { start: shiftDate(reference, -days), end: reference };
}
