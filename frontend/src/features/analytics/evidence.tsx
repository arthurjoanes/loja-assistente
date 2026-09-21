"use client";
import { useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icon";
import { api, ApiError } from "@/lib/api";
import type { Result } from "@/lib/contracts";
import { dateLabel } from "@/lib/format";
import { DataTable } from "./visualization";

export function EvidencePanel({
  answerId,
  onError,
}: {
  answerId: string;
  onError: (error: unknown) => void;
}) {
  const [evidence, setEvidence] = useState<Result | null>(null);
  const [evidenceLoading, setEvidenceLoading] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  async function loadEvidence() {
    if (evidence || evidenceLoading) return;
    setEvidenceLoading(true);
    setEvidenceError(null);
    try {
      const received = await api<Result>("/answers/" + answerId + "/evidence");
      if (mounted.current) setEvidence(received);
    } catch (error) {
      if (!mounted.current) return;
      setEvidenceError(
        error instanceof Error ? error.message : "Falha ao carregar o cálculo.",
      );
      if (error instanceof ApiError && error.status === 401) onError(error);
    } finally {
      if (mounted.current) setEvidenceLoading(false);
    }
  }
  return (
    <details
      className="evidence"
      onToggle={(event) => {
        if (event.currentTarget.open) void loadEvidence();
      }}
    >
      <summary>
        <span>
          <Icon name="list" size={17} /> Cálculo
        </span>
        <Icon name="chevron" size={16} />
      </summary>
      <div className="evidence-body">
        {evidenceLoading && (
          <p className="muted" role="status">
            <span className="spinner" /> Carregando cálculo…
          </p>
        )}
        {evidenceError && (
          <div className="notice danger" role="alert">
            {evidenceError}
            <button className="text-button" onClick={() => void loadEvidence()}>
              Tentar novamente
            </button>
          </div>
        )}
        {evidence && (
          <>
            <dl className="evidence-meta">
              <div>
                <dt>Fórmula</dt>
                <dd>{evidence.formula}</dd>
              </div>
              <div>
                <dt>Período consultado</dt>
                <dd>
                  {dateLabel(evidence.period.start)} (incluído) até{" "}
                  {dateLabel(evidence.period.end)} (excluído)
                </dd>
              </div>
              <div>
                <dt>Lojas e fuso</dt>
                <dd>
                  {evidence.scope
                    .map((store) => store.name + " (" + store.id + ")")
                    .join(", ")}{" "}
                  · {evidence.timezone}
                </dd>
              </div>
              <div>
                <dt>Fonte</dt>
                <dd>Dados fictícios · {evidence.dataset_version}</dd>
              </div>
              <div>
                <dt>Cobertura</dt>
                <dd>
                  {evidence.coverage.covered_days} /{" "}
                  {evidence.coverage.expected_days} combinações de loja e dia
                  carregadas
                </dd>
              </div>
            </dl>
            {evidence.evidence.length > 0 && (
              <DataTable rows={evidence.evidence} caption="Totais por dia" />
            )}
            {evidence.coverage.missing.length > 0 && (
              <details className="missing-days">
                <summary>
                  Ver {evidence.coverage.missing.length} combinações ausentes
                </summary>
                <ul>
                  {evidence.coverage.missing.map((item) => (
                    <li key={item.store_id + item.date}>
                      {item.store_id} · {dateLabel(item.date)}
                    </li>
                  ))}
                </ul>
              </details>
            )}
            <p className="request-id">
              ID da consulta <code>{evidence.request_id}</code>
            </p>
          </>
        )}
      </div>
    </details>
  );
}
