import type { Metric, Period, Row } from "./contracts";

export const metricLabels: Record<Metric, string> = {
  revenue: "Receita líquida",
  orders: "Pedidos concluídos",
  average_ticket: "Ticket médio",
  units: "Unidades vendidas",
};

// Centavos vêm como texto; inteiros evitam perda de precisão.
export function money(cents: string | number | null) {
  if (cents === null) return "Indisponível";
  const raw = String(cents);
  const negative = raw.startsWith("-");
  const [whole, fraction = ""] = raw.replace(/^-/, "").split(".");
  const rounded =
    BigInt(whole || "0") +
    (Number(fraction[0] ?? "0") >= 5 ? BigInt(1) : BigInt(0));
  const reais = (rounded / BigInt(100)).toLocaleString("pt-BR");
  return (
    (negative && rounded > 0 ? "−" : "") +
    "R$ " +
    reais +
    "," +
    String(rounded % BigInt(100)).padStart(2, "0")
  );
}
export function metricValue(value: string | number | null, metric: Metric) {
  if (value === null) return "Indisponível";
  return metric === "revenue" || metric === "average_ticket"
    ? money(value)
    : Number(value).toLocaleString("pt-BR");
}
export function rowValue(row: Row, metric: Metric): string | number | null {
  return metric === "revenue"
    ? row.revenue_cents
    : metric === "orders"
      ? row.orders
      : metric === "units"
        ? row.units
        : row.average_ticket_cents;
}
export function dateLabel(date: string, short = false) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: short ? "short" : "2-digit",
    ...(short ? {} : { year: "numeric" }),
    timeZone: "UTC",
  }).format(new Date(date + "T12:00:00Z"));
}
export function shiftDate(date: string, days: number) {
  const value = new Date(date + "T12:00:00Z");
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}
export function periodLabel(period: Period) {
  const last = shiftDate(period.end, -1);
  return period.start === last
    ? dateLabel(period.start)
    : dateLabel(period.start, true) + " – " + dateLabel(last, true);
}
