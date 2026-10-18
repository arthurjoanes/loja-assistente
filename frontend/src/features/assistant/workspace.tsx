"use client";
import { useEffect, useRef, useState } from "react";
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
import { FavoritesPanel } from "./favorites-panel";
import { ClarificationPanel } from "./clarification-panel";

export function Workspace() {
  const {
    session,
    booting,
    notice,
    error,
    setError,
    history,
    historyLoading,
    historyError,
    historyCursor,
    loadHistory,
    messagesNextCursor,
    loadOlderAnswers,
    favorites,
    favoritesLoading,
    favoritesError,
    conflict,
    success,
    pendingClarification,
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
    showFavorites,
    saveFavorite,
    renameFavorite,
    deleteFavorite,
    runFavorite,
    openRecordedCalculation,
    respondClarification,
    cancelClarification,
    reloadWorkspace,
  } = useWorkspace();
  const latestId = answers.at(-1)?.id;
  const [queryExpanded, setQueryExpanded] = useState(true);
  const [selection, setSelection] = useState<{
    conversationId: string | null;
    latestId: string | undefined;
    id: string;
  } | null>(null);
  const selectedId =
    selection?.conversationId === conversationId &&
    selection?.latestId === latestId
      ? selection.id
      : latestId;
  const resultStart = useRef<HTMLDivElement>(null);
  const pendingStart = useRef<HTMLDivElement>(null);
  const clarificationHeading = useRef<HTMLHeadingElement>(null);
  const errorNotice = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const editQuestionButton = useRef<HTMLButtonElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  function focusAnalysis(preferClarification = true) {
    requestAnimationFrame(() => {
      const target = preferClarification
        ? (clarificationHeading.current ?? resultStart.current)
        : resultStart.current;
      target?.focus();
      target?.scrollIntoView({ block: "start", behavior: "instant" });
    });
  }
  async function submitQuestion(text: string) {
    const answer = await ask(text);
    if (answer) focusAnalysis();
  }
  async function selectConversation(id: string) {
    const conversation = await openConversation(id);
    if (conversation) focusAnalysis();
  }
  async function confirmClarification(choiceId: string) {
    const answer = await respondClarification(choiceId);
    if (answer) focusAnalysis();
    return answer;
  }
  async function stopClarification() {
    const cancelled = await cancelClarification();
    if (cancelled) editQuestion();
    return cancelled;
  }
  useEffect(() => {
    if (!error && !pendingQuestion) return;
    const target = error
      ? errorNotice.current
      : (pendingStart.current ?? resultStart.current);
    if (error) target?.focus();
    target?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "start",
    });
  }, [pendingQuestion, error]);
  function startAnalysis() {
    freshConversation();
    setQueryExpanded(true);
    requestAnimationFrame(() => composer.current?.focus());
  }
  function editQuestion() {
    setQueryExpanded(true);
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
  const locked = busy || operationsLoading || favoritesLoading;
  const periodInvalid = !validPeriod(period);
  const hasResponse = answers.length > 0;
  const queryControls = (
    <aside
      key="query"
      id="query-controls"
      className={
        "query-panel" +
        (queryExpanded || !hasResponse ? "" : " query-panel-collapsed")
      }
      aria-label="Preparar consulta"
    >
      <div className="query-panel-heading">
        <Icon name="store" size={18} />
        <div>
          <h2>{hasResponse ? "Próxima consulta" : "Nova consulta"}</h2>
          <p>Defina o recorte e faça sua pergunta.</p>
        </div>
        <button
          className="query-collapse icon-button"
          hidden={!hasResponse}
          aria-label="Recolher próxima consulta"
          disabled={busy}
          onClick={() => {
            setQueryExpanded(false);
            editQuestionButton.current?.focus();
          }}
        >
          <Icon name="close" size={16} />
        </button>
      </div>
      <AnalysisFilters
        stores={session.user.stores}
        storeIds={storeIds}
        period={period}
        periodPreset={periodPreset}
        mode={mode}
        llmAvailable={session.llm_available}
        busy={busy || conflict}
        periodInvalid={periodInvalid}
        onStoresChange={setStoreIds}
        onPresetChange={choosePeriod}
        onModeChange={setMode}
        onPeriodChange={setPeriod}
      />
      <QuestionComposer
        mode={mode}
        llmAvailable={session.llm_available}
        hasPlan={answers.some((answer) => answer.plan !== null)}
        reviewingEarlier={selectedId !== latestId}
        busy={busy || conflict}
        periodInvalid={periodInvalid}
        question={question}
        textareaRef={composer}
        onQuestionChange={setQuestion}
        onAsk={(text) => void submitQuestion(text)}
      />
      <AnalysisContext
        stores={session.user.stores}
        referenceDate={session.reference_date}
        datasetVersion={session.dataset_version}
      />
    </aside>
  );

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
        historyLoading={historyLoading}
        historyError={historyError}
        historyHasMore={!!historyCursor}
        onReloadHistory={() => void loadHistory()}
        onOlderHistory={() => void loadHistory(true)}
        conversationId={conversationId}
        view={view}
        mobileMenu={mobileMenu}
        returnFocusTo={menuButton}
        locked={locked}
        onClose={() => setMobileMenu(false)}
        onNewAnalysis={startAnalysis}
        onShowAnalysis={() => setView("assistant")}
        onShowOperations={() => void showOperations()}
        onShowFavorites={() => void showFavorites()}
        onOpenConversation={(id) => void selectConversation(id)}
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
                {view === "assistant"
                  ? "Análise de vendas"
                  : view === "favorites"
                    ? "Favoritos"
                    : "Atendimentos"}
              </h1>
            </div>
          </div>
          <div className="reference-date">
            <span className="status-dot" />
            Data de referência
            <strong>{dateLabel(session.reference_date)}</strong>
          </div>
        </header>

        {(error || conflict) && (
          <div
            className="notice danger workspace-notice"
            role="alert"
            ref={errorNotice}
            tabIndex={-1}
          >
            <span>
              {error ??
                "Confira o estado atual para resolver a execução pendente antes de continuar."}
            </span>
            {conflict && (
              <button
                className="text-button"
                disabled={locked}
                onClick={() => void reloadWorkspace()}
              >
                Recarregar estado atual
              </button>
            )}
            {!conflict && (
              <button
                className="icon-button"
                aria-label="Fechar mensagem de erro"
                onClick={() => setError(null)}
              >
                <Icon name="close" size={16} />
              </button>
            )}
          </div>
        )}
        {success && (
          <p className="notice workspace-notice" role="status">
            {success}
          </p>
        )}

        {view === "operations" ? (
          <main id="main-content" className="operations-scroll" tabIndex={-1}>
            <OperationsPanel
              operations={operations}
              loading={operationsLoading}
              stale={operationsStale}
              onRefresh={() => void showOperations()}
            />
          </main>
        ) : view === "favorites" ? (
          <main id="main-content" className="operations-scroll" tabIndex={-1}>
            <FavoritesPanel
              favorites={favorites}
              stores={session.user.stores}
              loading={favoritesLoading}
              error={favoritesError}
              busy={busy}
              conflict={conflict}
              onRefresh={() => void showFavorites()}
              onAnalysis={() => setView("assistant")}
              onRename={renameFavorite}
              onDelete={deleteFavorite}
              onRun={async (favorite) => {
                const answer = await runFavorite(favorite);
                if (answer) focusAnalysis();
              }}
              onOpen={async (favorite) => {
                const focused = await openRecordedCalculation(favorite);
                if (focused) {
                  setSelection(focused);
                  focusAnalysis(false);
                }
              }}
            />
          </main>
        ) : (
          <main
            id="main-content"
            tabIndex={-1}
            className="explorer-layout"
            aria-busy={busy}
          >
            <div className="conversation-column" key="result">
              {messagesNextCursor && (
                <button
                  className="prepare-question"
                  disabled={busy}
                  onClick={() => void loadOlderAnswers()}
                >
                  Carregar respostas anteriores
                </button>
              )}
              {pendingClarification && (
                <ClarificationPanel
                  key={
                    pendingClarification.id +
                    ":" +
                    pendingClarification.revision
                  }
                  pending={pendingClarification}
                  stores={session.user.stores}
                  busy={busy}
                  conflict={conflict}
                  headingRef={clarificationHeading}
                  onRespond={confirmClarification}
                  onCancel={stopClarification}
                  onReload={() => void reloadWorkspace()}
                />
              )}
              {hasResponse && (
                <div className="result-toolbar">
                  {answers.length > 1 && (
                    <div className="result-selector">
                      <label htmlFor="result-selector" className="sr-only">
                        Resultados desta análise
                      </label>
                      <select
                        id="result-selector"
                        aria-label="Resultado selecionado"
                        value={selectedId}
                        disabled={busy}
                        onChange={(event) =>
                          setSelection({
                            conversationId,
                            latestId,
                            id: event.target.value,
                          })
                        }
                      >
                        {answers.map((answer, index) => (
                          <option key={answer.id} value={answer.id}>
                            {index + 1}. {answer.question}
                          </option>
                        ))}
                      </select>
                      <span>
                        {answers.findIndex(
                          (answer) => answer.id === selectedId,
                        ) + 1}{" "}
                        de {answers.length}
                      </span>
                    </div>
                  )}
                  <button
                    className="prepare-question"
                    ref={editQuestionButton}
                    aria-controls="query-controls"
                    disabled={busy}
                    onClick={editQuestion}
                  >
                    Editar pergunta <Icon name="arrow" size={14} />
                  </button>
                </div>
              )}
              <div className="conversation-scroll">
                {answers.length === 0 && !pendingQuestion ? (
                  <AnalysisStart
                    disabled={
                      busy ||
                      periodInvalid ||
                      (mode === "llm" && !session.llm_available)
                    }
                    onAsk={(text) => void submitQuestion(text)}
                  />
                ) : (
                  <div className="conversation-thread">
                    {pendingQuestion && (
                      <div className="pending-answer" ref={pendingStart}>
                        <div className="question-row">
                          <p>{pendingQuestion}</p>
                        </div>
                        <div className="loading-message" role="status">
                          <span className="spinner" />
                          Consultando…
                        </div>
                      </div>
                    )}
                    {answers.map((answer) => (
                      <div
                        key={answer.id}
                        hidden={answer.id !== selectedId}
                        ref={answer.id === selectedId ? resultStart : undefined}
                        tabIndex={-1}
                        className="analysis-result-focus"
                        role="region"
                        aria-label={`Resultado: ${answer.question}`}
                      >
                        <AnswerCard
                          answer={answer}
                          onError={handleError}
                          busy={busy || conflict}
                          clarificationActive={
                            pendingClarification?.status === "pending" &&
                            pendingClarification.id ===
                              answer.pending_clarification?.id
                          }
                          saved={favorites.some(
                            (favorite) =>
                              favorite.source_answer_id === answer.id,
                          )}
                          onSave={saveFavorite}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            {queryControls}
          </main>
        )}
      </div>
    </div>
  );
}
