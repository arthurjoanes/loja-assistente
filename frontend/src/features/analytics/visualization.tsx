"use client";
import { useState, type CSSProperties } from "react";
import { Icon } from "@/components/icon";
import { dailySeries } from "./daily-series";
import { rankingRevenueShare } from "./ranking-share";
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
  const revenueShare = rankingRevenueShare(result);
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
        <div
          className="segmented"
          role="group"
          aria-label="Visualização do resultado"
        >
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
      {revenueShare !== null && (
        <p className="ranking-concentration">
          <strong>{revenueShare}%</strong> da receita vem{" "}
          {result.rows.length === 1
            ? "deste produto"
            : `destes ${result.rows.length} produtos`}
          .
          {result.coverage.status === "partial"
            ? " Considera apenas os dados carregados."
            : ""}
        </p>
      )}
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
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const { points, axisIndices, maximumValue } = dailySeries(
    result.rows,
    result.metric,
    result.period,
  );
  const pointLabel = (point: (typeof points)[number]) =>
    `${dateLabel(point.date)}: ${point.row ? metricValue(point.value, result.metric) : "Sem dados carregados"}`;
  const selected =
    points.find((point) => point.date === selectedDate) ?? points.at(-1);
  return (
    <figure className="daily-overview">
      <div className="daily-chart" role="group" aria-label="Evolução diária">
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
        >
          {points.map((point, index) => (
            <button
              type="button"
              className={
                "daily-column" +
                (point.date === selected?.date ? " selected" : "")
              }
              key={point.date}
              aria-label={pointLabel(point)}
              aria-pressed={point.date === selected?.date}
              tabIndex={point.date === selected?.date ? 0 : -1}
              onClick={() => setSelectedDate(point.date)}
              onFocus={() => setSelectedDate(point.date)}
              onKeyDown={(event) => {
                const next =
                  event.key === "ArrowRight"
                    ? Math.min(points.length - 1, index + 1)
                    : event.key === "ArrowLeft"
                      ? Math.max(0, index - 1)
                      : event.key === "Home"
                        ? 0
                        : event.key === "End"
                          ? points.length - 1
                          : null;
                if (next === null) return;
                event.preventDefault();
                const button =
                  event.currentTarget.parentElement?.children.item(next);
                if (button instanceof HTMLButtonElement) button.focus();
              }}
            >
              {point.value === null ? (
                <span className="daily-missing" />
              ) : (
                <span
                  className="daily-bar"
                  style={
                    { "--column-scale": point.height / 100 } as CSSProperties
                  }
                />
              )}
            </button>
          ))}
        </div>
        <div className="daily-axis" aria-hidden="true">
          {axisIndices.map((index) => (
            <span key={points[index].date}>
              {dateLabel(points[index].date, true)}
            </span>
          ))}
        </div>
        {selected && (
          <p className="daily-selection" aria-live="polite">
            <span>{dateLabel(selected.date)}</span>
            <strong>
              {selected.row
                ? metricValue(selected.value, result.metric)
                : "Sem dados carregados"}
            </strong>
          </p>
        )}
      </div>
      <figcaption>
        {points.length === 1 ? "1 dia" : `${points.length} dias`} · Selecione
        uma coluna para ver o valor.
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
