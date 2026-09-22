import type { Metric, Period, Row } from "@/lib/contracts";
import { rowValue } from "@/lib/format";

export function dailySeries(rows: Row[], metric: Metric, period: Period) {
  const start = Date.parse(period.start + "T00:00:00Z");
  const end = Date.parse(period.end + "T00:00:00Z");
  const byDate = new Map(rows.map((row) => [row.key, row]));
  // Datas comerciais são posições no calendário, sem conversão de fuso.
  // Uma data sem linha mantém a lacuna; não fabrica venda zero ou linha de tabela.
  const dates = Array.from({ length: (end - start) / 86_400_000 }, (_, index) =>
    new Date(start + index * 86_400_000).toISOString().slice(0, 10),
  );
  const values = dates.map((date) => {
    const row = byDate.get(date);
    return row ? rowValue(row, metric) : null;
  });
  // Conversão numérica só para geometria; os valores originais seguem na tabela.
  const magnitudes = values.map((value) => Math.max(0, Number(value ?? 0)));
  const maximum = Math.max(1, ...magnitudes);
  const axisIndices = [
    ...new Set([0, Math.floor((dates.length - 1) / 2), dates.length - 1]),
  ].filter((index) => index >= 0 && index < dates.length);
  return {
    points: dates.map((date, index) => ({
      date,
      row: byDate.get(date) ?? null,
      value: values[index],
      height: (magnitudes[index] / maximum) * 100,
    })),
    axisIndices,
  };
}
