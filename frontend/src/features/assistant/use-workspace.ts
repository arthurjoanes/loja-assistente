"use client";
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type {
  Answer,
  Conversation,
  ConversationDetail,
  Favorite,
  Mode,
  Operations,
  PendingClarification,
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
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [favoritesLoading, setFavoritesLoading] = useState(false);
  const [favoritesError, setFavoritesError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [view, setView] = useState<"assistant" | "operations" | "favorites">(
    "assistant",
  );
  const [mobileMenu, setMobileMenu] = useState(false);
  const [operations, setOperations] = useState<Operations | null>(null);
  const [operationsLoading, setOperationsLoading] = useState(false);
  const generation = useRef(0);
  const historyRevision = useRef(0);
  const favoritesRevision = useRef(0);
  const analysisRevision = useRef(0);
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
    pendingClarification,
  } = analysis;
  const requestActive = useRef(false);
  const [operationsStale, setOperationsStale] = useState(false);
  const setQuestion = (value: string) => dispatch({ type: "question", value });
  const setMode = (value: Mode) => dispatch({ type: "mode", value });
  const setStoreIds = (value: string[]) => dispatch({ type: "stores", value });
  const setPeriod = (value: Period) =>
    dispatch({ type: "period", value, preset: "custom" });

  const fetchFavorites = useCallback(
    async (
      currentGeneration: number,
      revision: number,
      isActive?: () => boolean,
    ) => {
      try {
        const saved = await api<Favorite[]>("/favorites");
        if (
          (!isActive || isActive()) &&
          generation.current === currentGeneration &&
          revision === favoritesRevision.current
        ) {
          setFavorites(saved);
          setFavoritesError(null);
        }
        return saved;
      } catch (received) {
        if (
          (!isActive || isActive()) &&
          generation.current === currentGeneration &&
          revision === favoritesRevision.current
        )
          setFavoritesError(
            received instanceof Error
              ? received.message
              : "Não foi possível carregar os favoritos. Tente recarregar.",
          );
        throw received;
      }
    },
    [],
  );

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
        const favoriteRevision = ++favoritesRevision.current;
        const [conversations] = await Promise.all([
          api<Conversation[]>("/conversations"),
          fetchFavorites(currentGeneration, favoriteRevision, () => active),
        ]);
        if (
          active &&
          generation.current === currentGeneration &&
          revision === historyRevision.current
        )
          setHistory(conversations);
        const pending = conversations.find(
          (item) => item.pending_clarification?.status === "pending",
        );
        if (pending && active && generation.current === currentGeneration) {
          const detail = await api<ConversationDetail>(
            `/conversations/${pending.id}`,
          );
          if (active && generation.current === currentGeneration)
            dispatch({
              type: "conversation",
              value: detail,
              stores: current.user.stores.map((store) => store.id),
            });
        }
      })
      .catch((error) => {
        if (!active || generation.current !== currentGeneration) return;
        if (error instanceof ApiError && error.status === 401) {
          generation.current += 1;
          setSession(null);
          dispatch({ type: "reset" });
          setHistory([]);
          setFavorites([]);
          setFavoritesError(null);
          if (authenticated) setNotice("Sessão expirada. Entre novamente.");
        } else if (error instanceof ApiError && error.status === 403) {
          generation.current += 1;
          setSession(null);
          dispatch({ type: "reset" });
          setHistory([]);
          setFavorites([]);
          setFavoritesError(null);
          setNotice("Acesso alterado. Entre novamente.");
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
  }, [fetchFavorites]);

  function clearSession(message: string | null) {
    generation.current += 1;
    dispatch({ type: "reset" });
    requestActive.current = false;
    setOperationsStale(false);
    setOperationsLoading(false);
    setSession(null);
    setHistory([]);
    setFavorites([]);
    setFavoritesError(null);
    setFavoritesLoading(false);
    setConflict(false);
    setSuccess(null);
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
      if (error instanceof ApiError && error.status === 403) {
        generation.current += 1;
        const currentGeneration = generation.current;
        dispatch({ type: "reset" });
        setHistory([]);
        setFavorites([]);
        setFavoritesError(null);
        setOperations(null);
        setOperationsLoading(false);
        setOperationsStale(true);
        setBusy(false);
        setFavoritesLoading(false);
        setConflict(false);
        setPendingQuestion(null);
        setSuccess(null);
        requestActive.current = false;
        setSession((current) =>
          current
            ? { ...current, user: { ...current.user, stores: [] } }
            : null,
        );
        void api<Session>("/auth/me")
          .then((current) => {
            if (generation.current !== currentGeneration) return;
            setSession(current);
            setStoreIds(current.user.stores.map((store) => store.id));
          })
          .catch((received) => {
            if (
              generation.current === currentGeneration &&
              received instanceof ApiError &&
              received.status === 401
            )
              clearSession("Sessão expirada. Entre novamente.");
          });
      }
      if (error instanceof ApiError && error.status === 409) setConflict(true);
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
    const favoriteRevision = ++favoritesRevision.current;
    const analysisVersion = ++analysisRevision.current;
    dispatch({
      type: "reset",
      stores: current.user.stores.map((store) => store.id),
    });
    setFavorites([]);
    setFavoritesError(null);
    setHistory([]);
    setSuccess(null);
    setConflict(false);
    setSession(current);
    setNotice(null);
    setStoreIds(current.user.stores.map((store) => store.id));
    try {
      const [conversations] = await Promise.all([
        api<Conversation[]>("/conversations"),
        fetchFavorites(currentGeneration, favoriteRevision),
      ]);
      if (
        generation.current === currentGeneration &&
        revision === historyRevision.current
      )
        setHistory(conversations);
      const pending = conversations.find(
        (item) => item.pending_clarification?.status === "pending",
      );
      if (
        pending &&
        generation.current === currentGeneration &&
        analysisVersion === analysisRevision.current
      ) {
        const detail = await api<ConversationDetail>(
          `/conversations/${pending.id}`,
        );
        if (
          generation.current === currentGeneration &&
          analysisVersion === analysisRevision.current
        )
          dispatch({
            type: "conversation",
            value: detail,
            stores: current.user.stores.map((store) => store.id),
          });
      }
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
    analysisRevision.current += 1;
    dispatch({
      type: "reset",
      stores: session?.user.stores.map((store) => store.id) ?? [],
      mode,
    });
    setError(null);
    setSuccess(null);
    setConflict(false);
    setView("assistant");
    setMobileMenu(false);
  }
  async function openConversation(id: string) {
    const analysisVersion = ++analysisRevision.current;
    const currentGeneration = generation.current;
    setBusy(true);
    setError(null);
    setMobileMenu(false);
    try {
      const conversation = await api<ConversationDetail>(
        "/conversations/" + id,
      );
      if (
        currentGeneration !== generation.current ||
        analysisVersion !== analysisRevision.current
      )
        return;
      dispatch({
        type: "conversation",
        value: conversation,
        stores: session?.user.stores.map((store) => store.id) ?? [],
      });
      setView("assistant");
      setConflict(false);
      return conversation;
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
    analysisRevision.current += 1;
    const currentGeneration = generation.current;
    setBusy(true);
    setError(null);
    setSuccess(null);
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
      setConflict(false);
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
      if (generation.current === currentGeneration) return answer;
    } catch (error) {
      if (currentGeneration === generation.current) {
        handleError(error);
        if (!(error instanceof ApiError && [401, 403].includes(error.status)))
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
  async function refreshLists(currentGeneration: number) {
    const historyVersion = ++historyRevision.current;
    const favoriteVersion = ++favoritesRevision.current;
    const [conversations] = await Promise.all([
      api<Conversation[]>("/conversations"),
      fetchFavorites(currentGeneration, favoriteVersion),
    ]);
    if (generation.current !== currentGeneration) return;
    if (historyVersion === historyRevision.current) setHistory(conversations);
  }
  async function showFavorites() {
    const currentGeneration = generation.current;
    const revision = ++favoritesRevision.current;
    setView("favorites");
    setMobileMenu(false);
    setFavoritesLoading(true);
    setError(null);
    try {
      await fetchFavorites(currentGeneration, revision);
      if (
        generation.current === currentGeneration &&
        revision === favoritesRevision.current
      ) {
        setConflict(false);
      }
    } catch (received) {
      if (generation.current === currentGeneration) handleError(received);
    } finally {
      if (generation.current === currentGeneration) setFavoritesLoading(false);
    }
  }
  async function perform<T>(
    path: string,
    body: unknown,
    onComplete: (value: T) => void,
    message: string,
    execution = false,
  ) {
    if (
      !session ||
      busy ||
      operationsLoading ||
      requestActive.current ||
      conflict
    )
      return false;
    requestActive.current = true;
    const currentGeneration = generation.current;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const received = await api<T>(path, { body, csrf: session.csrf_token });
      if (generation.current !== currentGeneration) return false;
      onComplete(received);
      setSuccess(message);
      return true;
    } catch (received) {
      if (generation.current === currentGeneration) {
        handleError(received);
        if (
          execution &&
          received instanceof ApiError &&
          [0, 408, 503, 504].includes(received.status)
        ) {
          setConflict(true);
          setError(
            "Não foi possível confirmar a execução. Verifique o histórico e recarregue o estado antes de executar outra vez; a consulta pode ter sido concluída.",
          );
        }
      }
      return false;
    } finally {
      if (generation.current === currentGeneration) {
        requestActive.current = false;
        setBusy(false);
      }
    }
  }
  function receiveFavorite(favorite: Favorite) {
    setFavorites((current) =>
      [favorite, ...current.filter((item) => item.id !== favorite.id)].slice(
        0,
        50,
      ),
    );
  }
  function saveFavorite(answerId: string, name: string) {
    return perform<Favorite>(
      "/favorites",
      { answer_id: answerId, name },
      receiveFavorite,
      "Consulta salva nos favoritos.",
    );
  }
  function renameFavorite(favorite: Favorite, name: string) {
    return perform<Favorite>(
      `/favorites/${favorite.id}/rename`,
      { revision: favorite.revision, name },
      receiveFavorite,
      "Nome do favorito atualizado.",
    );
  }
  function deleteFavorite(favorite: Favorite) {
    return perform<void>(
      `/favorites/${favorite.id}/delete`,
      { revision: favorite.revision },
      () => {
        setFavorites((current) =>
          current.filter((item) => item.id !== favorite.id),
        );
      },
      "Favorito excluído.",
    );
  }
  async function runFavorite(favorite: Favorite) {
    const currentGeneration = generation.current;
    let receivedAnswer: Answer | undefined;
    const completed = await perform<Answer>(
      `/favorites/${favorite.id}/run`,
      { revision: favorite.revision },
      (answer) => {
        receivedAnswer = answer;
        analysisRevision.current += 1;
        dispatch({
          type: "reset",
          stores: session?.user.stores.map((store) => store.id) ?? [],
        });
        dispatch({ type: "answer", value: answer });
        setView("assistant");
      },
      "Nova execução registrada. O cálculo anterior permanece no histórico.",
      true,
    );
    if (completed && generation.current === currentGeneration) {
      try {
        await refreshLists(currentGeneration);
      } catch (received) {
        if (generation.current === currentGeneration) handleError(received);
      }
      if (generation.current === currentGeneration) return receivedAnswer;
    }
  }
  async function openRecordedCalculation(favorite: Favorite) {
    if (!session || busy || requestActive.current) return;
    const currentGeneration = generation.current;
    const analysisVersion = ++analysisRevision.current;
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const answer = await api<Answer>(`/answers/${favorite.source_answer_id}`);
      if (
        generation.current !== currentGeneration ||
        analysisVersion !== analysisRevision.current
      )
        return;
      const conversation = await api<ConversationDetail>(
        `/conversations/${answer.conversation_id}`,
      );
      if (
        generation.current !== currentGeneration ||
        analysisVersion !== analysisRevision.current
      )
        return;
      dispatch({
        type: "conversation",
        value: conversation,
        stores: session.user.stores.map((store) => store.id),
      });
      setView("assistant");
      setSuccess(
        "Cálculo registrado aberto. Nenhuma nova execução foi solicitada.",
      );
      return {
        conversationId: conversation.id,
        latestId: conversation.messages.at(-1)?.id,
        id: answer.id,
      };
    } catch (received) {
      if (generation.current === currentGeneration) handleError(received);
    } finally {
      if (generation.current === currentGeneration) setBusy(false);
    }
  }
  async function respondClarification(choiceId: string) {
    if (
      !pendingClarification ||
      pendingClarification.status !== "pending" ||
      !conversationId
    )
      return;
    let receivedAnswer: Answer | undefined;
    const completed = await perform<Answer>(
      `/conversations/${conversationId}/clarification/respond`,
      {
        pending_id: pendingClarification.id,
        revision: pendingClarification.revision,
        choice_id: choiceId,
      },
      (answer) => {
        receivedAnswer = answer;
        dispatch({ type: "answer", value: answer });
      },
      "Escolha registrada.",
      true,
    );
    return completed ? receivedAnswer : undefined;
  }
  function cancelClarification() {
    if (
      !pendingClarification ||
      pendingClarification.status !== "pending" ||
      !conversationId
    )
      return Promise.resolve(false);
    return perform<PendingClarification>(
      `/conversations/${conversationId}/clarification/cancel`,
      {
        pending_id: pendingClarification.id,
        revision: pendingClarification.revision,
      },
      (received) => dispatch({ type: "clarification", value: received }),
      "Esclarecimento cancelado.",
    );
  }
  async function reloadWorkspace() {
    const currentGeneration = generation.current;
    setBusy(true);
    setError(null);
    try {
      const detail = conversationId
        ? api<ConversationDetail>(`/conversations/${conversationId}`)
        : Promise.resolve(null);
      const [conversation] = await Promise.all([
        detail,
        refreshLists(currentGeneration),
      ]);
      if (generation.current !== currentGeneration) return;
      if (conversation)
        dispatch({
          type: "conversation",
          value: conversation,
          stores: session?.user.stores.map((store) => store.id) ?? [],
          preserveDraft: true,
        });
      setConflict(false);
      setSuccess(
        "Dados recarregados. Confira o estado atual antes de continuar.",
      );
    } catch (received) {
      if (generation.current === currentGeneration) handleError(received);
    } finally {
      if (generation.current === currentGeneration) setBusy(false);
    }
  }
  return {
    session,
    booting,
    notice,
    error,
    setError,
    history,
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
  };
}
