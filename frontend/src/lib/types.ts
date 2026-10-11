export type View = "chat" | "records" | "documents" | "memory";
export type RecordKind = "metric" | "diet" | "exercise";
export type Session = {
  user_id: string;
  model_mode: "fake" | "provider";
  timezone: string;
  memory_enabled: boolean;
};
export type Thread = {
  thread_id: string;
  created_at: string;
  active_request_id: string | null;
  title?: string;
  status?: string;
  can_resume?: boolean;
};
export type Message = { role: "user" | "assistant"; content: string };
export type ThreadState = Thread & { messages: Message[]; pending: boolean };
export type ToolResult<T> = {
  success: boolean;
  data: T | null;
  error_code: string | null;
  error_message: string | null;
  retryable: boolean;
};
export type HealthRecord = {
  id: string;
  metric_type?: "weight" | "heart_rate" | "sleep_duration" | "steps";
  value?: number;
  unit?: string;
  measured_at?: string;
  food_name?: string;
  amount?: string;
  meal_type?: string;
  nutrition_info?: { calories?: number | null } | null;
  exercise_type?: string;
  duration?: number;
  distance?: number | null;
  calories?: number | null;
  timestamp?: string;
};
export type HealthDocument = {
  id: string;
  filename: string;
  document_type: string;
  created_at: string;
  parse_status: string;
  index_status: string;
  error_code?: string | null;
  visibility?: string;
};
export type Preference = {
  key: string;
  value: string;
  updated_at: string;
  source_request_id: string;
  source_thread_id: string | null;
};
export type MemoryData = {
  preferences: Preference[];
  allowed_values: Record<string, string[]>;
};
export type ChatInput = {
  message: string;
  thread_id?: string;
  request_id: string;
};
export type ChatResult = {
  answer: string;
  thread_id: string;
  request_id: string;
  run_id: string;
  trace_id: string;
  model_mode: "fake" | "provider";
  termination_reason: "completed";
  memory_updates: { key: string; value: string | null }[];
};
export type StreamEvent = {
  event:
    | "run.started"
    | "message.delta"
    | "tool.started"
    | "tool.finished"
    | "run.completed"
    | "run.failed";
  data: {
    version: number;
    seq: number;
    trace_id: string;
    run_id: string | null;
    thread_id: string | null;
    request_id?: string;
    text?: string;
    name?: string;
    tool_call_id?: string;
    success?: boolean;
    error_code?: string | null;
    error_message?: string;
    answer?: string;
    [key: string]: unknown;
  };
};
