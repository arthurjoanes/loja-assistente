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
    <details className="context-panel">
      <summary>
        <Icon name="shield" size={15} />
        Dados fictícios · acesso e métricas
        <Icon name="chevron" size={14} />
      </summary>
      <div className="context-content">
        <section>
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
        </section>
        <section>
          <h2 className="context-label">Sobre os dados</h2>
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
        </section>
        <section>
          <h2 className="context-label">Métricas disponíveis</h2>
          <p>
            Receita líquida, pedidos concluídos, ticket médio, unidades, ranking
            e evolução diária.
          </p>
        </section>
      </div>
    </details>
  );
}
