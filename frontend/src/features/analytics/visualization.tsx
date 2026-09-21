"use client";
import { useState } from "react";
import { Icon } from "@/components/icon";
import type { Result, Row } from "@/lib/contracts";
import {
  dateLabel,
  metricLabels,
  metricValue,
  money,
  rowValue,
} from "@/lib/format";

export function ResultChart({ result }: { result: Result }) {
  const [view, setView] = useState<"chart" | "table">("chart");
  const ranking = result.intent === "ranking";
  // Number só calcula a geometria. Rótulos usam centavos decimais.
  const max = Math.max(
    1,
    ...result.rows.map((row) => Number(rowValue(row, result.metric) ?? 0)),
  );
  return (
    <section className="chart-panel">
      <header className="chart-header">
        <div>
          <h3>
            {ranking ? "Ranking por " : "Evolução de "}
            {metricLabels[result.metric].toLowerCase()}
          </h3>
        </div>
        <div className="segmented" aria-label="Visualização do resultado">
          <button
            className={view === "chart" ? "active" : ""}
            aria-pressed={view === "chart"}
            onClick={() => setView("chart")}
          >
            <Icon name="chart" size={15} />
            Gráfico
          </button>
          <button
            className={view === "table" ? "active" : ""}
            aria-pressed={view === "table"}
            onClick={() => setView("table")}
          >
            <Icon name="list" size={15} />
            Tabela
          </button>
        </div>
      </header>
      {view === "table" ? (
        <DataTable
          rows={result.rows}
          caption={
            ranking
              ? "Produtos classificados pela métrica consultada"
              : "Série por dia comercial"
          }
        />
      ) : (
        <div
          className={"bar-chart " + (ranking ? "ranking-chart" : "daily-chart")}
          role="img"
          aria-label={
            (ranking ? "Ranking" : "Evolução") +
            ": " +
            result.rows
              .map(
                (row) =>
                  row.label +
                  ", " +
                  metricValue(rowValue(row, result.metric), result.metric),
              )
              .join("; ")
          }
        >
          {result.rows.map((row, index) => (
            <div className="chart-row" key={row.key}>
              <span className="chart-label">
                {ranking && <small>{String(index + 1).padStart(2, "0")}</small>}
                {ranking
                  ? row.label
                  : /^\d{4}-\d{2}-\d{2}$/.test(row.label)
                    ? dateLabel(row.label, true)
                    : row.label}
              </span>
              <span className="bar-track">
                <span
                  className={"bar " + (index === 0 ? "bar-first" : "")}
                  style={{
                    width:
                      (Math.max(0, Number(rowValue(row, result.metric) ?? 0)) /
                        max) *
                        100 +
                      "%",
                  }}
                />
              </span>
              <strong className="chart-value">
                {metricValue(rowValue(row, result.metric), result.metric)}
              </strong>
            </div>
          ))}
        </div>
      )}
      <p className="chart-footnote">
        {" "}
        {result.metric === "average_ticket"
          ? "Ticket indisponível quando não há pedidos."
          : "Somente pedidos concluídos."}
      </p>
    </section>
  );
}
export function DataTable({ rows, caption }: { rows: Row[]; caption: string }) {
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label={caption}
    >
      <table>
        <caption>{caption}</caption>
        <thead>
          <tr>
            <th scope="col">Referência</th>
            <th scope="col">Receita</th>
            <th scope="col">Pedidos</th>
            <th scope="col">Unidades</th>
            <th scope="col">Ticket</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key}>
              <th scope="row">{row.label}</th>
              <td>{money(row.revenue_cents)}</td>
              <td>{row.orders.toLocaleString("pt-BR")}</td>
              <td>{row.units.toLocaleString("pt-BR")}</td>
              <td>{money(row.average_ticket_cents)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
