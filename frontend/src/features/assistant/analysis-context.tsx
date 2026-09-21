import { Icon } from "@/components/icon";
import type { Store } from "@/lib/contracts";
import { dateLabel, shiftDate } from "@/lib/format";

export function AnalysisContext({
  stores,
  referenceDate,
  datasetVersion,
}: {
  stores: Store[];
  referenceDate: string;
  datasetVersion: string;
}) {
  return (
    <aside className="context-panel" aria-label="Contexto da análise">
      <h2 className="context-label">
        <Icon name="shield" size={17} /> Acesso da conta
      </h2>
      <div className="authorized-stores">
        {stores.map((store) => (
          <span className="store-tag" key={store.id}>
            <Icon name="check" size={13} />
            {store.name}
          </span>
        ))}
      </div>
      <p className="context-note">
        Selecione as lojas da próxima consulta no filtro.
      </p>
      <details className="capabilities">
        <summary>
          Sobre os dados <Icon name="chevron" size={14} />
        </summary>
        <dl className="dataset-details">
          <div>
            <dt>Fonte</dt>
            <dd>
              Dados fictícios<small>{datasetVersion}</small>
            </dd>
          </div>
          <div>
            <dt>Fuso comercial</dt>
            <dd>America/Sao_Paulo</dd>
          </div>
          <div>
            <dt>Referência analítica</dt>
            <dd>
              {dateLabel(referenceDate)}
              <small>
                “Ontem” é {dateLabel(shiftDate(referenceDate, -1))}.
              </small>
            </dd>
          </div>
        </dl>
      </details>
      <details className="capabilities">
        <summary>
          Métricas disponíveis <Icon name="chevron" size={14} />
        </summary>
        <p>
          Receita líquida, pedidos concluídos, ticket médio, unidades, ranking e
          evolução diária.
        </p>
      </details>
    </aside>
  );
}
