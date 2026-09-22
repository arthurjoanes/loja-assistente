"use client";
import { useState, type CSSProperties } from "react";
import { Icon } from "@/components/icon";
import { dailySeries } from "./daily-series";
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
      ) : !ranking ? (
        <DailyChart result={result} />
      ) : (
        <div
          className="bar-chart ranking-chart"
          tabIndex={0}
          role="img"
          aria-label={
            "Ranking" +
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
                <small>{String(index + 1).padStart(2, "0")}</small>
                {row.label}
              </span>
              <span className="bar-track">
                <span
                  className="bar"
                  style={
                    {
                      "--bar-size":
                        (Math.max(
                          0,
                          Number(rowValue(row, result.metric) ?? 0),
                        ) /
                          max) *
                          100 +
                        "%",
                    } as CSSProperties
                  }
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
function DailyChart({ result }: { result: Result }) {
  const { points, axisIndices, maximumValue } = dailySeries(
    result.rows,
    result.metric,
    result.period,
  );
  const pointLabel = (point: (typeof points)[number]) =>
    `${dateLabel(point.date)}: ${point.row ? metricValue(point.value, result.metric) : "Sem dados carregados"}`;
  return (
    <figure className="daily-overview">
      <div
        className="daily-chart"
        role="img"
        aria-label={"Evolução diária. " + points.map(pointLabel).join("; ")}
      >
        <div className="daily-scale" aria-hidden="true">
          <span>Base: {metricValue(0, result.metric)}</span>
          <strong>
            {maximumValue === null
              ? "Sem valores disponíveis"
              : `Teto: ${metricValue(maximumValue, result.metric)}`}
          </strong>
        </div>
        <div
          className="daily-bars"
          style={{ "--points": points.length } as CSSProperties}
          aria-hidden="true"
        >
          {points.map((point) => (
            <div
              className="daily-column"
              key={point.date}
              title={pointLabel(point)}
            >
              {point.value === null ? (
                <span className="daily-missing" />
              ) : (
                <span
                  className="daily-bar"
                  style={{ height: point.height + "%" }}
                />
              )}
            </div>
          ))}
        </div>
        <div className="daily-axis" aria-hidden="true">
          {axisIndices.map((index) => (
            <span key={points[index].date}>
              {dateLabel(points[index].date, true)}
            </span>
          ))}
        </div>
      </div>
      <figcaption>
        {points.length === 1 ? "1 dia" : `${points.length} dias`} · Colunas a
        partir de zero. Valores exatos em Tabela.
        {points.some(({ value }) => value === null) &&
          " Traço: dado ausente ou valor indisponível."}
      </figcaption>
    </figure>
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
            <th scope="col" className="numeric">
              Receita
            </th>
            <th scope="col" className="numeric">
              Pedidos
            </th>
            <th scope="col" className="numeric">
              Unidades
            </th>
            <th scope="col" className="numeric">
              Ticket
            </th>
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
