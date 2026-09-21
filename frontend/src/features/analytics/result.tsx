"use client";
import { Icon } from "@/components/icon";
import type { Answer, Metric, Result, Totals } from "@/lib/contracts";
import { metricLabels, metricValue, periodLabel } from "@/lib/format";
import { EvidencePanel } from "./evidence";
import { ResultChart } from "./visualization";

export function AnswerCard({
  answer,
  onError,
}: {
  answer: Answer;
  onError: (error: unknown) => void;
}) {
  const result = answer.result;
  return (
    <article className="answer-block" data-testid="answer">
      <div className="question-row">
        <p>{answer.question}</p>
      </div>
      <div className="answer-head">
        <span className="assistant-mark">
          <Icon
            name={
              result
                ? result.intent === "aggregate"
                  ? "grid"
                  : "chart"
                : "info"
            }
            size={18}
          />
        </span>
        <h2>
          {result
            ? result.intent === "daily"
              ? "Evolução diária"
              : result.intent === "ranking"
                ? "Ranking de produtos"
                : "Resumo do período"
            : answer.status === "needs_clarification"
              ? "Reformule a pergunta"
              : "Consulta não concluída"}
        </h2>
        <span className="answer-mode">
          {answer.mode === "demo" ? "DEMO" : "IA"}
        </span>
      </div>
      <div className="answer-content">
        <p
          className={
            "answer-message " +
            (answer.status !== "ready" ? "answer-limitation" : "")
          }
        >
          {answer.message}
        </p>
        {result && (
          <>
            <div className="result-context" aria-label="Lojas consultadas">
              <span>
                <Icon name="store" size={14} />
                {result.scope.map((store) => store.name).join(" + ")}
              </span>
              <span>
                <Icon name="calendar" size={14} />
                {periodLabel(result.period)}
              </span>
              <span className={"coverage " + result.coverage.status}>
                <span className="status-dot" />
                {result.coverage.status === "complete"
                  ? "Cobertura completa"
                  : result.coverage.status === "partial"
                    ? "Cobertura parcial"
                    : "Sem dados carregados"}
              </span>
            </div>
            {result.coverage.status === "partial" && (
              <div className="notice warning">
                Apenas {result.coverage.covered_days} de{" "}
                {result.coverage.expected_days} combinações de loja e dia
                carregadas. Totais parciais.
              </div>
            )}
            {result.totals && result.coverage.status !== "absent" && (
              <>
                <MetricSummary
                  totals={result.totals}
                  metric={result.metric}
                  intent={result.intent}
                />
                {result.comparison && (
                  <div className="comparison">
                    <Icon name="chart" size={18} />
                    <div>
                      <strong>
                        {result.comparison.change_percent !== null
                          ? result.comparison.change_percent.replace(".", ",") +
                            "% em relação ao período anterior"
                          : "Comparação percentual indisponível"}
                      </strong>
                      <p>
                        {periodLabel(result.comparison.period)} ·{" "}
                        {metricValue(result.comparison.value, result.metric)}.{" "}
                        {result.comparison.message}
                      </p>
                    </div>
                  </div>
                )}
                {(result.intent === "ranking" || result.intent === "daily") &&
                  result.rows.length > 0 && <ResultChart result={result} />}
              </>
            )}
            <EvidencePanel answerId={answer.id} onError={onError} />
          </>
        )}
        {!result && (
          <p className="answer-help">
            {answer.status === "provider_error"
              ? "Selecione demo para continuar."
              : "Use receita, pedidos, ticket, unidades, ranking ou evolução diária."}
          </p>
        )}
      </div>
    </article>
  );
}
function MetricSummary({
  totals,
  metric,
  intent,
}: {
  totals: Totals;
  metric: Metric;
  intent: Result["intent"];
}) {
  const values: Record<Metric, number | string | null> = {
    revenue: totals.revenue_cents,
    orders: totals.orders,
    average_ticket: totals.average_ticket_cents,
    units: totals.units,
  };
  const otherMetrics = (Object.keys(values) as Metric[]).filter(
    (item) => item !== metric,
  );
  return (
    <section className="period-summary" aria-label="Indicadores do período">
      <dl className="metric-summary">
        <div className="primary-metric">
          <dt>{metricLabels[metric]}</dt>
          <dd>{metricValue(values[metric], metric)}</dd>
        </div>
        {otherMetrics.map((item) => (
          <div className="context-metric" key={item}>
            <dt>{metricLabels[item]}</dt>
            <dd>{metricValue(values[item], item)}</dd>
          </div>
        ))}
      </dl>
      {intent === "ranking" && (
        <p className="summary-note">
          O total inclui todos os produtos das lojas e do período consultados.
        </p>
      )}
    </section>
  );
}
