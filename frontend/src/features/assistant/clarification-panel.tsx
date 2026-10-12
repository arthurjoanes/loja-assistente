"use client";
import { useEffect, useState } from "react";
import type { PendingClarification, Store } from "@/lib/contracts";
import { PlanScope } from "./plan-scope";

export function ClarificationPanel({
  pending,
  stores,
  busy,
  conflict,
  onRespond,
  onCancel,
  onReload,
}: {
  pending: PendingClarification;
  stores: Store[];
  busy: boolean;
  conflict: boolean;
  onRespond: (choiceId: string) => Promise<boolean>;
  onCancel: () => Promise<boolean>;
  onReload: () => void;
}) {
  const [choiceId, setChoiceId] = useState("");
  const [expired, setExpired] = useState(
    () => Date.parse(pending.expires_at) <= Date.now(),
  );
  useEffect(() => {
    const timeout = window.setTimeout(
      () => setExpired(true),
      Math.max(0, Date.parse(pending.expires_at) - Date.now()),
    );
    return () => window.clearTimeout(timeout);
  }, [pending.expires_at]);
  const choice = pending.choices.find((item) => item.id === choiceId);
  const preview = {
    ...pending.partial_plan,
    ...(choice?.period ? { period: choice.period } : {}),
    ...(choice?.store_ids ? { store_ids: choice.store_ids } : {}),
  };
  if (pending.status !== "pending")
    return (
      <p className="clarification-state" role="status">
        {pending.status === "cancelled"
          ? "Esclarecimento cancelado. Faça uma nova pergunta para continuar."
          : pending.status === "expired"
            ? "Esclarecimento expirado. Faça a pergunta novamente."
            : "Esclarecimento concluído."}
      </p>
    );
  return (
    <section
      className="clarification-panel"
      aria-labelledby={`clarification-${pending.id}`}
    >
      <h3 id={`clarification-${pending.id}`}>
        {pending.missing_field === "period"
          ? "Qual período deseja consultar?"
          : "Qual loja deseja consultar?"}
      </h3>
      <p>Pergunta: {pending.original_question}</p>
      {expired ? (
        <p role="status">
          Este esclarecimento expirou. Recarregue para conferir o estado e faça
          a pergunta novamente.
        </p>
      ) : (
        <form
          onSubmit={async (event) => {
            event.preventDefault();
            if (choice && !busy && !conflict) await onRespond(choice.id);
          }}
        >
          <fieldset disabled={busy || conflict}>
            <legend>
              {pending.missing_field === "period"
                ? "Escolha o período"
                : "Escolha a loja"}
            </legend>
            {pending.choices.map((item) => (
              <label className="clarification-choice" key={item.id}>
                <input
                  type="radio"
                  name={`clarification-${pending.id}`}
                  value={item.id}
                  checked={choiceId === item.id}
                  onChange={() => setChoiceId(item.id)}
                />
                {item.label}
              </label>
            ))}
          </fieldset>
          <div
            className="clarification-preview"
            aria-label="Escopo a confirmar"
          >
            <h4>Confira o escopo</h4>
            <PlanScope plan={preview} stores={stores} />
          </div>
          <p className="scope-guidance">
            O indicador e as lojas já resolvidos são preservados. O período
            informado na pergunta prevalece sobre o filtro visual. A escolha usa
            a referência analítica da sessão.
          </p>
          <div className="favorite-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={!choice || busy || conflict}
            >
              {busy ? "Confirmando…" : "Confirmar escolha"}
            </button>
            <button
              type="button"
              className="text-button"
              disabled={busy || conflict}
              onClick={() => void onCancel()}
            >
              Cancelar esclarecimento
            </button>
          </div>
        </form>
      )}
      {(expired || conflict) && (
        <button className="text-button" disabled={busy} onClick={onReload}>
          Recarregar esclarecimento
        </button>
      )}
      <p className="muted">
        Expira em{" "}
        <time dateTime={pending.expires_at}>
          {new Date(pending.expires_at).toLocaleString("pt-BR", {
            timeZone: "America/Sao_Paulo",
            dateStyle: "short",
            timeStyle: "short",
          })}
        </time>
        .
      </p>
    </section>
  );
}
