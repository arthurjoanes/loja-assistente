import { Icon } from "@/components/icon";
import type { Operations } from "@/lib/contracts";

const capabilityLabels: Record<string, string> = {
  aggregate: "Resumo",
  ranking: "Ranking de produtos",
  daily: "Evolução diária",
  unknown: "Não interpretado",
  none: "Não interpretado",
};
const statusLabels: Record<string, string> = {
  ready: "Concluído",
  needs_clarification: "Esclarecimento",
  unsupported: "Fora de escopo",
  provider_error: "Erro no provedor",
  no_data: "Sem dados",
  error: "Erro",
  forbidden: "Acesso recusado",
  denied: "Acesso recusado",
  conflict: "Conversa ocupada",
};

export function OperationsPanel({
  operations,
  loading,
  stale,
  onRefresh,
}: {
  operations: Operations | null;
  loading: boolean;
  stale: boolean;
  onRefresh: () => void;
}) {
  return (
    <section className="operations-panel">
      <div className="section-heading">
        <div>
          <h2>Atendimentos</h2>
          <p className="muted">Últimas 100 consultas da conta.</p>
        </div>
        <button
          className="button secondary"
          disabled={loading}
          onClick={onRefresh}
        >
          <Icon name="refresh" size={16} />
          Atualizar
        </button>
      </div>
      {loading && (
        <p role="status" className="loading-message">
          <span className="spinner" />
          Carregando…
        </p>
      )}
      {stale && (
        <p role="status" className="notice warning">
          Falha ao atualizar os atendimentos.
          {operations ? " Exibindo a última consulta." : " Tente novamente."}
        </p>
      )}
      {operations && (
        <>
          <div className="operation-stats">
            <div>
              <span>Consultas</span>
              <strong>{operations.total}</strong>
            </div>
            <div>
              <span>Erros</span>
              <strong>{operations.errors}</strong>
            </div>
            <div>
              <span>Tokens / custo</span>
              <strong className="not-applicable">Indisponível</strong>
              <small>Não expostos neste painel</small>
            </div>
          </div>
          {operations.entries.length ? (
            <div
              className="table-scroll operation-table"
              tabIndex={0}
              role="region"
              aria-label="Histórico de consultas"
            >
              <table>
                <caption>Duração no serviço, antes de gravar o log.</caption>
                <thead>
                  <tr>
                    <th>Horário</th>
                    <th>Modo / capacidade</th>
                    <th>Status</th>
                    <th className="numeric">Interpretação</th>
                    <th className="numeric">Consulta</th>
                    <th
                      className="numeric"
                      title="Tempo no serviço, sem commit ou rede"
                    >
                      Serviço
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {operations.entries.map((entry) => (
                    <tr key={entry.request_id}>
                      <td>
                        <time dateTime={entry.created_at}>
                          {new Date(entry.created_at).toLocaleString("pt-BR")}
                        </time>
                        <details className="operation-details">
                          <summary>Ver detalhes</summary>
                          <small className="operation-request">
                            {entry.request_id}
                          </small>
                          <small className="operation-request">
                            {entry.interpreter_version}
                          </small>
                        </details>
                      </td>
                      <td>
                        {entry.mode === "demo" ? "Demonstração" : "IA"} ·{" "}
                        {capabilityLabels[entry.capability] ??
                          "Não interpretado"}
                      </td>
                      <td>
                        <span
                          className={
                            "pill " +
                            (entry.status === "ready" ? "success" : "neutral")
                          }
                        >
                          {statusLabels[entry.status] ?? "Não concluído"}
                        </span>
                      </td>
                      <td className="numeric">
                        {entry.interpretation_ms.toLocaleString("pt-BR")} ms
                      </td>
                      <td className="numeric">
                        {entry.query_ms.toLocaleString("pt-BR")} ms
                      </td>
                      <td className="numeric">
                        {entry.response_ms.toLocaleString("pt-BR")} ms
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-operations">
              <Icon name="clock" size={30} />
              <h3>Nenhuma consulta</h3>
            </div>
          )}
        </>
      )}
    </section>
  );
}
