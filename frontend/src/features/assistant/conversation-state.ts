import type {
  Answer,
  ConversationDetail,
  Mode,
  PendingClarification,
  Period,
} from "@/lib/contracts";

export type AnalysisState = {
  conversationId: string | null;
  answers: Answer[];
  question: string;
  mode: Mode;
  storeIds: string[];
  period: Period | null;
  periodPreset: string;
  pendingClarification: PendingClarification | null;
  messagesNextCursor: string | null;
};

export function emptyAnalysis(
  storeIds: string[] = [],
  mode: Mode = "demo",
): AnalysisState {
  return {
    conversationId: null,
    answers: [],
    question: "",
    mode,
    storeIds,
    period: null,
    periodPreset: "question",
    pendingClarification: null,
    messagesNextCursor: null,
  };
}

type AnalysisAction =
  | { type: "reset"; stores?: string[]; mode?: Mode }
  | { type: "question"; value: string }
  | { type: "mode"; value: Mode }
  | { type: "stores"; value: string[] }
  | { type: "period"; value: Period | null; preset: string }
  | { type: "clarification"; value: PendingClarification | null }
  | { type: "answer"; value: Answer }
  | { type: "older_answers"; items: Answer[]; nextCursor: string | null }
  | {
      type: "conversation";
      value: ConversationDetail;
      stores: string[];
      preserveDraft?: boolean;
    };

export function analysisReducer(
  state: AnalysisState,
  action: AnalysisAction,
): AnalysisState {
  switch (action.type) {
    case "reset":
      return emptyAnalysis(action.stores, action.mode);
    case "question":
      return { ...state, question: action.value };
    case "mode":
      return { ...state, mode: action.value };
    case "stores":
      return { ...state, storeIds: action.value };
    case "period":
      return { ...state, period: action.value, periodPreset: action.preset };
    case "clarification":
      return { ...state, pendingClarification: action.value };
    case "answer": {
      const answer = action.value;
      const sameConversation = state.conversationId === answer.conversation_id;
      return {
        ...state,
        conversationId: answer.conversation_id,
        answers: [
          ...(sameConversation
            ? state.answers.filter((item) => item.id !== answer.id)
            : []),
          answer,
        ],
        messagesNextCursor: sameConversation ? state.messagesNextCursor : null,
        pendingClarification: answer.pending_clarification ?? null,
        period: answer.plan?.period ?? state.period,
        periodPreset: answer.plan ? "effective" : state.periodPreset,
        storeIds:
          answer.result?.scope.map((store) => store.id) ?? state.storeIds,
      };
    }
    case "older_answers":
      return {
        ...state,
        answers: [
          ...action.items,
          ...state.answers.filter(
            (item) => !action.items.some((older) => older.id === item.id),
          ),
        ],
        messagesNextCursor: action.nextCursor,
      };
    case "conversation": {
      if (action.preserveDraft)
        return {
          ...state,
          conversationId: action.value.id,
          answers: action.value.messages,
          messagesNextCursor: action.value.messages_next_cursor ?? null,
          pendingClarification: action.value.pending_clarification ?? null,
        };
      const last = action.value.messages.findLast(
        (answer) => answer.plan !== null,
      );
      return {
        ...state,
        conversationId: action.value.id,
        answers: action.value.messages,
        messagesNextCursor: action.value.messages_next_cursor ?? null,
        pendingClarification: action.value.pending_clarification ?? null,
        period: last?.plan?.period ?? null,
        periodPreset: last?.plan ? "effective" : "question",
        storeIds: last?.result?.scope.map((store) => store.id) ?? action.stores,
      };
    }
  }
}
