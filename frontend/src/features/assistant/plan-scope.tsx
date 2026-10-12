import type { PartialPlan, Plan, Store } from "@/lib/contracts";
import { dateLabel, metricLabels } from "@/lib/format";

export function PlanScope({
  plan,
  stores,
}: {
  plan: Plan | PartialPlan;
  stores: Store[];
}) {
  const ids = "store_ids" in plan ? plan.store_ids : plan.store_references;
  return (
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
            ? ids
                .map((id) => {
                  const store = stores.find((item) => item.id === id);
                  return store ? `${store.name} (${id})` : id;
                })
                .join(" + ")
            : "Aguardando escolha da loja"}
        </dd>
      </div>
      <div>
        <dt>Período</dt>
        <dd>
          {plan.period
            ? `${dateLabel(plan.period.start)} (incluído) até ${dateLabel(plan.period.end)} (excluído)`
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
  );
}
