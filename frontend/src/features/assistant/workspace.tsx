"use client";
import { useEffect, useRef } from "react";
import { Brand, Icon } from "@/components/icon";
import { dateLabel } from "@/lib/format";
import { AnswerCard } from "@/features/analytics/result";
import { Login } from "./login";
import { OperationsPanel } from "./operations";
import { AnalysisSidebar } from "./analysis-sidebar";
import { AnalysisFilters } from "./analysis-filters";
import { AnalysisContext } from "./analysis-context";
import { AnalysisStart } from "./analysis-start";
import { QuestionComposer } from "./question-composer";
import { useWorkspace } from "./use-workspace";
import { validPeriod } from "./period-selection";

export function Workspace() {
  const {
    session,
    booting,
    notice,
    error,
    setError,
    history,
    conversationId,
    answers,
    question,
    setQuestion,
    busy,
    pendingQuestion,
    mode,
    setMode,
    storeIds,
    setStoreIds,
    period,
    setPeriod,
    periodPreset,
    view,
    setView,
    mobileMenu,
    setMobileMenu,
    operations,
    operationsLoading,
    operationsStale,
    signedIn,
    logout,
    freshConversation,
    openConversation,
    ask,
    showOperations,
    choosePeriod,
    handleError,
  } = useWorkspace();
  const conversationEnd = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    conversationEnd.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "end",
    });
  }, [answers, pendingQuestion]);
  function startAnalysis() {
    freshConversation();
    requestAnimationFrame(() => composer.current?.focus());
  }
  if (booting)
    return (
      <main className="boot-screen">
        <Brand />
        <p role="status">
          <span className="spinner" />
          Carregando…
        </p>
      </main>
    );
  if (!session)
    return (
      <Login onLogin={(current) => void signedIn(current)} notice={notice} />
    );
  const locked = busy || operationsLoading;
  const periodInvalid = !validPeriod(period);

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Ir para o conteúdo
      </a>
      {mobileMenu && (
        <button
          className="sidebar-backdrop"
          onClick={() => setMobileMenu(false)}
          aria-label="Fechar navegação"
        />
      )}
      <AnalysisSidebar
        user={session.user}
        history={history}
        conversationId={conversationId}
        view={view}
        mobileMenu={mobileMenu}
        returnFocusTo={menuButton}
        locked={locked}
        onClose={() => setMobileMenu(false)}
        onNewAnalysis={startAnalysis}
        onShowAnalysis={() => setView("assistant")}
        onShowOperations={() => void showOperations()}
        onOpenConversation={(id) => void openConversation(id)}
        onSignOut={() => void logout()}
      />

      <div className="workspace" inert={mobileMenu}>
        <header className="workspace-header">
          <div className="workspace-title">
            <button
              className="icon-button mobile-only"
              aria-label="Abrir menu"
              ref={menuButton}
              onClick={() => setMobileMenu(true)}
            >
              <Icon name="menu" />
            </button>
            <div>
              <span className="breadcrumb">
                {session.user.organization.name}
              </span>
              <h1>
                {view === "assistant" ? "Análise de vendas" : "Atendimentos"}
              </h1>
            </div>
          </div>
          <div className="reference-date">
            <span className="status-dot" />
            Data de referência
            <strong>{dateLabel(session.reference_date)}</strong>
          </div>
        </header>

        {view === "assistant" && (
          <AnalysisFilters
            stores={session.user.stores}
            storeIds={storeIds}
            period={period}
            periodPreset={periodPreset}
            mode={mode}
            llmAvailable={session.llm_available}
            busy={busy}
            periodInvalid={periodInvalid}
            onStoresChange={setStoreIds}
            onPresetChange={choosePeriod}
            onModeChange={setMode}
            onPeriodChange={setPeriod}
          />
        )}
        {error && (
          <div className="notice danger workspace-notice" role="alert">
            <span>{error}</span>
            <button
              className="icon-button"
              aria-label="Fechar mensagem de erro"
              onClick={() => setError(null)}
            >
              <Icon name="close" size={16} />
            </button>
          </div>
        )}

        {view === "operations" ? (
          <main id="main-content" className="operations-scroll">
            <OperationsPanel
              operations={operations}
              loading={operationsLoading}
              stale={operationsStale}
              onRefresh={() => void showOperations()}
            />
          </main>
        ) : (
          <div className="assistant-layout">
            <div className="conversation-column">
              <main
                id="main-content"
                className="conversation-scroll"
                aria-busy={busy}
              >
                {answers.length === 0 && !pendingQuestion ? (
                  <AnalysisStart
                    disabled={
                      busy ||
                      periodInvalid ||
                      (mode === "llm" && !session.llm_available)
                    }
                    onAsk={(text) => void ask(text)}
                  />
                ) : (
                  <div className="conversation-thread">
                    {answers.map((answer) => (
                      <AnswerCard
                        key={answer.id}
                        answer={answer}
                        onError={handleError}
                      />
                    ))}
                    {pendingQuestion && (
                      <div className="pending-answer">
                        <div className="question-row">
                          <p>{pendingQuestion}</p>
                        </div>
                        <div className="loading-message" role="status">
                          <span className="spinner" />
                          Consultando…
                        </div>
                      </div>
                    )}
                    <div ref={conversationEnd} />
                  </div>
                )}
              </main>
              <QuestionComposer
                mode={mode}
                llmAvailable={session.llm_available}
                hasPlan={answers.some((answer) => answer.plan !== null)}
                busy={busy}
                periodInvalid={periodInvalid}
                question={question}
                textareaRef={composer}
                onQuestionChange={setQuestion}
                onAsk={(text) => void ask(text)}
              />
            </div>
            <AnalysisContext
              stores={session.user.stores}
              referenceDate={session.reference_date}
              datasetVersion={session.dataset_version}
            />
          </div>
        )}
      </div>
    </div>
  );
}
