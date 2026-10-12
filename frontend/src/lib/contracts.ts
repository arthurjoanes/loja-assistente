export type Store = { id: string; name: string };
export type Period = { start: string; end: string };
export type Metric = "revenue" | "orders" | "average_ticket" | "units";
export type Mode = "demo" | "llm";
export type Session = {
  user: {
    id: string;
    name: string;
    email: string;
    role: string;
    organization: { id: string; name: string };
    stores: Store[];
  };
  csrf_token: string;
  reference_date: string;
  dataset_version: string;
  llm_available: boolean;
};
export type Plan = {
  intent: "aggregate" | "ranking" | "daily";
  metric: Metric;
  store_references: string[];
  period: Period;
  comparison: "previous_period" | null;
  grouping: "day" | null;
  limit: number;
};
export type Favorite = {
  id: string;
  name: string;
  plan: Plan;
  schema_version: 1;
  source_answer_id: string;
  created_at: string;
  updated_at: string;
  revision: number;
};
export type PartialPlan = Omit<Plan, "store_references" | "period"> & {
  store_ids: string[];
  period: Period | null;
};
export type ClarificationChoice = {
  id: string;
  label: string;
  period: Period | null;
  store_ids: string[] | null;
};
export type PendingClarification = {
  id: string;
  revision: number;
  status: "pending" | "resolved" | "cancelled" | "expired";
  original_question: string;
  partial_plan: PartialPlan;
  missing_field: "period" | "store";
  choices: ClarificationChoice[];
  created_at: string;
  expires_at: string;
  schema_version: 1;
  mode: Mode;
  reference_date: string;
};
export type SaveFavoriteRequest = { answer_id: string; name: string };
export type FavoriteRevisionRequest = { revision: number };
export type RenameFavoriteRequest = FavoriteRevisionRequest & { name: string };
export type ClarificationRevisionRequest = {
  pending_id: string;
  revision: number;
};
export type RespondClarificationRequest = ClarificationRevisionRequest & {
  choice_id: string;
};
export type Totals = {
  revenue_cents: string;
  orders: number;
  units: number;
  average_ticket_cents: string | null;
};
export type Row = Totals & { key: string; label: string };
export type Result = {
  intent: Plan["intent"];
  metric: Metric;
  scope: Store[];
  period: Period;
  timezone: string;
  currency: string;
  unit: string;
  formula: string;
  value: string | null;
  totals: Totals | null;
  rows: Row[];
  coverage: {
    status: "complete" | "partial" | "absent";
    covered_days: number;
    expected_days: number;
    missing: { store_id: string; date: string }[];
  };
  comparison: {
    period: Period;
    value: string | null;
    change_percent: string | null;
    message: string;
  } | null;
  evidence: Row[];
  dataset_version: string;
  request_id: string;
};
export type Answer = {
  id: string;
  conversation_id: string;
  question: string;
  status:
    | "ready"
    | "needs_clarification"
    | "unsupported"
    | "provider_error"
    | "no_data";
  message: string;
  mode: Mode;
  plan: Plan | null;
  result: Result | null;
  request_id: string;
  created_at: string;
  pending_clarification?: PendingClarification | null;
  clarification_response?: {
    pending_id: string;
    revision: number;
    choice_id: string;
    label: string;
  } | null;
};
export type Conversation = {
  id: string;
  title: string;
  created_at: string;
  pending_clarification?: PendingClarification | null;
};
export type ConversationDetail = Conversation & {
  messages: Answer[];
  pending_clarification?: PendingClarification | null;
};
export type Operations = {
  entries: {
    request_id: string;
    mode: Mode;
    capability: string;
    status: string;
    interpretation_ms: number;
    query_ms: number;
    response_ms: number;
    created_at: string;
    interpreter_version: string;
  }[];
  total: number;
  errors: number;
  tokens: null;
  cost: null;
};
