"use client";
import { useState } from "react";
import { Brand, Icon } from "@/components/icon";
import { api, ApiError } from "@/lib/api";
import type { Session } from "@/lib/contracts";

const accounts = [
  {
    email: "gerente.a@demo.local",
    label: "Gerente · Aurora Casa",
    scope: "Loja Centro",
    initial: "A",
  },
  {
    email: "supervisor.a@demo.local",
    label: "Supervisor · Aurora Casa",
    scope: "Lojas Centro e Jardins",
    initial: "A",
  },
  {
    email: "gerente.b@demo.local",
    label: "Gerente · Brisa Casa",
    scope: "Loja Centro",
    initial: "B",
  },
];
export function Login({
  onLogin,
  notice,
}: {
  onLogin: (session: Session) => void;
  notice: string | null;
}) {
  const [email, setEmail] = useState(accounts[0].email);
  const [password, setPassword] = useState("LojaDemo!2026");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [credentialError, setCredentialError] = useState(false);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setCredentialError(false);
    try {
      onLogin(await api<Session>("/auth/login", { body: { email, password } }));
    } catch (error) {
      setCredentialError(
        error instanceof ApiError && [401, 422].includes(error.status),
      );
      setError(error instanceof Error ? error.message : "Falha ao entrar.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <section className="login-intro">
        <Brand />
        <div>
          <span className="eyebrow">Análise de vendas</span>
          <h2>Vendas, com o cálculo à vista.</h2>
          <p>
            Consulte um período, explore o resultado e confira de onde veio cada
            número.
          </p>
          <ol className="login-steps">
            <li>
              <strong>Defina o recorte</strong>
              <span>Lojas autorizadas e período da consulta.</span>
            </li>
            <li>
              <strong>Leia o resultado</strong>
              <span>Indicadores, ranking ou evolução diária.</span>
            </li>
            <li>
              <strong>Confira o cálculo</strong>
              <span>Fórmula, totais por dia e cobertura dos dados.</span>
            </li>
          </ol>
        </div>
        <p className="login-demo-note">
          Ambiente demonstrativo · dados fictícios
        </p>
      </section>
      <section className="login-form-panel">
        <div className="login-form-inner">
          <h1>Entrar</h1>
          <p className="muted">
            Escolha o acesso para explorar a demonstração.
          </p>
          {notice && (
            <div role="status" className="notice warning">
              {notice}
            </div>
          )}
          <form onSubmit={submit}>
            <fieldset className="account-options">
              <legend className="field-label">Conta</legend>
              {accounts.map((account) => (
                <label
                  className={
                    "account-option " +
                    (email === account.email ? "selected" : "")
                  }
                  key={account.email}
                >
                  <input
                    type="radio"
                    name="account"
                    value={account.email}
                    checked={email === account.email}
                    onChange={() => setEmail(account.email)}
                    disabled={busy}
                  />
                  <span className="account-avatar">{account.initial}</span>
                  <span className="account-copy">
                    <strong>{account.label}</strong>
                    <small>{account.scope}</small>
                  </span>
                  {email === account.email && <Icon name="check" size={18} />}
                </label>
              ))}
            </fieldset>
            <label className="field-label" htmlFor="password">
              Senha
            </label>
            <input
              id="password"
              className="text-input"
              type="password"
              value={password}
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
              required
              maxLength={200}
              aria-invalid={credentialError}
              aria-describedby={error ? "login-error" : "password-hint"}
              disabled={busy}
            />
            <p id="password-hint" className="input-hint">
              Senha local: <code>LojaDemo!2026</code>
            </p>
            {error && (
              <div id="login-error" className="notice danger" role="alert">
                {error}
              </div>
            )}
            <button
              className="button primary login-button"
              type="submit"
              disabled={busy}
            >
              {busy ? (
                <>
                  <span className="spinner" /> Entrando…
                </>
              ) : (
                <>
                  Entrar <Icon name="arrow" />
                </>
              )}
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}
