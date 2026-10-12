import type { PartialPlan, Plan, Store } from "@/lib/contracts";
import { dateLabel, metricLabels, shiftDate } from "@/lib/format";

export function PlanScope({
  plan,
  stores,
}: {
  plan: Plan | PartialPlan;
  stores: Store[];
}) {
  const ids = "store_ids" in plan ? plan.store_ids : plan.store_references;
  const names = ids.map((id) => {
    const store = stores.find((item) => item.id === id);
    return { id, name: store?.name ?? id };
  });
  const includedEnd = plan.period ? shiftDate(plan.period.end, -1) : null;
  return (
    <>
      <dl className="plan-scope">
        <div>
          <dt>Indicador</dt>
          <dd>
            {metricLabels[plan.metric]}
            {plan.intent === "ranking"
              ? ` · ranking de ${plan.limit} produtos`
              : plan.intent === "daily"
                ? " · evolução diária"
                : ""}
          </dd>
        </div>
        <div>
          <dt>Lojas</dt>
          <dd>
            {ids.length
              ? names.map((store) => store.name).join(" + ")
              : "Aguardando escolha da loja"}
          </dd>
        </div>
        <div>
          <dt>Período</dt>
          <dd>
            {plan.period
              ? plan.period.start === includedEnd
                ? dateLabel(plan.period.start)
                : `${dateLabel(plan.period.start)} a ${dateLabel(includedEnd!)}`
              : "Aguardando escolha do período"}
          </dd>
        </div>
        {plan.comparison && (
          <div>
            <dt>Comparação</dt>
            <dd>Período anterior de mesma duração</dd>
          </div>
        )}
      </dl>
      {(ids.length > 0 || plan.period) && (
        <details className="scope-details">
          <summary>Identificadores e limites do período</summary>
          <dl>
            {ids.length > 0 && (
              <div>
                <dt>Lojas no cálculo</dt>
                <dd>
                  {names
                    .map((store) => `${store.name} (${store.id})`)
                    .join(" + ")}
                </dd>
              </div>
            )}
            {plan.period && (
              <div>
                <dt>Intervalo da consulta</dt>
                <dd>
                  {dateLabel(plan.period.start)} (incluído) até{" "}
                  {dateLabel(plan.period.end)} (excluído)
                </dd>
              </div>
            )}
          </dl>
        </details>
      )}
    </>
  );
}
