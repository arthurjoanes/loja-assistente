import type { Answer, ConversationDetail, Mode, Period } from "@/lib/contracts";

export type AnalysisState = {
  conversationId: string | null;
  answers: Answer[];
  question: string;
  mode: Mode;
  storeIds: string[];
  period: Period | null;
  periodPreset: string;
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
  };
}

type AnalysisAction =
  | { type: "reset"; stores?: string[]; mode?: Mode }
  | { type: "question"; value: string }
  | { type: "mode"; value: Mode }
  | { type: "stores"; value: string[] }
  | { type: "period"; value: Period | null; preset: string }
  | { type: "answer"; value: Answer }
  | { type: "conversation"; value: ConversationDetail; stores: string[] };

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
    case "answer": {
      const answer = action.value;
      return {
        ...state,
        conversationId: answer.conversation_id,
        answers: [...state.answers, answer],
        period: answer.plan?.period ?? state.period,
        periodPreset: answer.plan ? "effective" : state.periodPreset,
        storeIds:
          answer.result?.scope.map((store) => store.id) ?? state.storeIds,
      };
    }
    case "conversation": {
      const last = action.value.messages.findLast(
        (answer) => answer.plan !== null,
      );
      return {
        ...state,
        conversationId: action.value.id,
        answers: action.value.messages,
        period: last?.plan?.period ?? null,
        periodPreset: last?.plan ? "effective" : "question",
        storeIds: last?.result?.scope.map((store) => store.id) ?? action.stores,
      };
    }
  }
}
