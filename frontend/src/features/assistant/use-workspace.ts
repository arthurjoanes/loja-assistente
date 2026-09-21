"use client";
import { useEffect, useReducer, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type {
  Answer,
  Conversation,
  ConversationDetail,
  Mode,
  Operations,
  Period,
  Session,
} from "@/lib/contracts";
import { analysisReducer, emptyAnalysis } from "./conversation-state";
import { selectPeriod, validPeriod } from "./period-selection";

export function useWorkspace() {
  const [session, setSession] = useState<Session | null>(null);
  const [booting, setBooting] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<Conversation[]>([]);
  const [busy, setBusy] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [view, setView] = useState<"assistant" | "operations">("assistant");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [operations, setOperations] = useState<Operations | null>(null);
  const [operationsLoading, setOperationsLoading] = useState(false);
  const generation = useRef(0);
  const historyRevision = useRef(0);
  const [analysis, dispatch] = useReducer(analysisReducer, undefined, () =>
    emptyAnalysis(),
  );
  const {
    conversationId,
    answers,
    question,
    mode,
    storeIds,
    period,
    periodPreset,
  } = analysis;
  const requestActive = useRef(false);
  const [operationsStale, setOperationsStale] = useState(false);
  const setQuestion = (value: string) => dispatch({ type: "question", value });
  const setMode = (value: Mode) => dispatch({ type: "mode", value });
  const setStoreIds = (value: string[]) => dispatch({ type: "stores", value });
  const setPeriod = (value: Period) =>
    dispatch({ type: "period", value, preset: "custom" });

  useEffect(() => {
    let active = true;
    let authenticated = false;
    const currentGeneration = generation.current;
    api<Session>("/auth/me")
      .then(async (current) => {
        if (!active || generation.current !== currentGeneration) return;
        authenticated = true;
        setSession(current);
        dispatch({
          type: "stores",
          value: current.user.stores.map((store) => store.id),
        });
        const revision = ++historyRevision.current;
        const conversations = await api<Conversation[]>("/conversations");
        if (
          active &&
          generation.current === currentGeneration &&
          revision === historyRevision.current
        )
          setHistory(conversations);
      })
      .catch((error) => {
        if (!active || generation.current !== currentGeneration) return;
        if (error instanceof ApiError && error.status === 401) {
          setSession(null);
          dispatch({ type: "reset" });
          setHistory([]);
          if (authenticated) setNotice("Sessão expirada. Entre novamente.");
        } else {
          setNotice(
            error instanceof Error ? error.message : "Serviço indisponível.",
          );
        }
      })
      .finally(() => {
        if (active) setBooting(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function clearSession(message: string | null) {
    generation.current += 1;
    dispatch({ type: "reset" });
    requestActive.current = false;
    setOperationsStale(false);
    setOperationsLoading(false);
    setSession(null);
    setHistory([]);
    setError(null);
    setNotice(message);
    setOperations(null);
    setView("assistant");
    setMobileMenu(false);
    setBusy(false);
    setPendingQuestion(null);
  }
  function handleError(error: unknown) {
    if (error instanceof ApiError && error.status === 401) {
      clearSession("Sessão expirada. Entre novamente.");
    } else {
      setError(
        error instanceof Error
          ? error.message
          : "Falha na consulta. Tente novamente.",
      );
    }
  }
  async function signedIn(current: Session) {
    generation.current += 1;
    const currentGeneration = generation.current;
    const revision = ++historyRevision.current;
    setSession(current);
    setNotice(null);
    setStoreIds(current.user.stores.map((store) => store.id));
    try {
      const conversations = await api<Conversation[]>("/conversations");
      if (
        generation.current === currentGeneration &&
        revision === historyRevision.current
      )
        setHistory(conversations);
    } catch (error) {
      if (
        generation.current === currentGeneration &&
        revision === historyRevision.current
      )
        handleError(error);
    }
  }
  async function logout() {
    if (!session) return;
    setBusy(true);
    try {
      await api("/auth/logout", { body: {}, csrf: session.csrf_token });
      clearSession(null);
    } catch (error) {
      handleError(error);
    } finally {
      setBusy(false);
    }
  }
  function freshConversation() {
    dispatch({
      type: "reset",
      stores: session?.user.stores.map((store) => store.id) ?? [],
      mode,
    });
    setError(null);
    setView("assistant");
    setMobileMenu(false);
  }
  async function openConversation(id: string) {
    const currentGeneration = generation.current;
    setBusy(true);
    setError(null);
    setMobileMenu(false);
    try {
      const conversation = await api<ConversationDetail>(
        "/conversations/" + id,
      );
      if (currentGeneration !== generation.current) return;
      dispatch({
        type: "conversation",
        value: conversation,
        stores: session?.user.stores.map((store) => store.id) ?? [],
      });
      setView("assistant");
    } catch (error) {
      if (currentGeneration === generation.current) handleError(error);
    } finally {
      if (currentGeneration === generation.current) setBusy(false);
    }
  }
  async function ask(text: string) {
    if (
      !session ||
      busy ||
      operationsLoading ||
      requestActive.current ||
      !text.trim() ||
      !validPeriod(period) ||
      (mode === "llm" && !session.llm_available)
    )
      return;
    requestActive.current = true;
    const currentGeneration = generation.current;
    setBusy(true);
    setError(null);
    setPendingQuestion(text.trim());
    setQuestion("");
    setView("assistant");
    try {
      const answer = await api<Answer>("/assistant/query", {
        body: {
          question: text.trim(),
          conversation_id: conversationId,
          mode,
          store_ids: storeIds,
          period,
        },
        csrf: session.csrf_token,
      });
      if (currentGeneration !== generation.current) return;
      dispatch({ type: "answer", value: answer });
      const revision = ++historyRevision.current;
      try {
        const conversations = await api<Conversation[]>("/conversations");
        if (
          generation.current === currentGeneration &&
          revision === historyRevision.current
        )
          setHistory(conversations);
      } catch (error) {
        if (
          generation.current === currentGeneration &&
          revision === historyRevision.current
        )
          handleError(error);
      }
    } catch (error) {
      if (currentGeneration === generation.current) {
        handleError(error);
        if (!(error instanceof ApiError && error.status === 401))
          setQuestion(text);
      }
    } finally {
      if (currentGeneration === generation.current) {
        requestActive.current = false;
        setBusy(false);
        setPendingQuestion(null);
      }
    }
  }
  async function showOperations() {
    setView("operations");
    setMobileMenu(false);
    setError(null);
    setOperationsLoading(true);
    const currentGeneration = generation.current;
    try {
      const data = await api<Operations>("/operations");
      if (currentGeneration === generation.current) {
        setOperations(data);
        setOperationsStale(false);
      }
    } catch (error) {
      if (currentGeneration === generation.current) {
        setOperationsStale(true);
        handleError(error);
      }
    } finally {
      if (currentGeneration === generation.current) setOperationsLoading(false);
    }
  }
  function choosePeriod(value: string) {
    if (!session) return;
    dispatch({
      type: "period",
      value: selectPeriod(value, session.reference_date, period),
      preset: value,
    });
  }
  return {
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
  };
}
