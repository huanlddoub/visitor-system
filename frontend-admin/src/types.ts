export type RequirementType = "general" | "pickup" | "dropoff" | "hotel" | "meal";
export type TaskStatus =
  | "pending_assignment"
  | "assigned"
  | "in_progress"
  | "completed"
  | "exception";

export interface User {
  id: number;
  name: string;
  phone?: string;
  role: "admin" | "receptionist";
  department?: string;
  skills?: Record<string, unknown>;
  available_status: string;
}

export interface Requirement {
  id: number;
  type: RequirementType;
  detail: Record<string, unknown>;
  status: TaskStatus;
}

export interface VisitorBrief {
  id: number;
  name: string;
  company: string;
  phone: string;
  visit_time: string;
  people_count: number;
}

export interface Task {
  id: number;
  visitor_id: number;
  requirement_id: number;
  task_type: RequirementType;
  visitor?: VisitorBrief;
  assignee_id?: number;
  assignee?: User;
  status: TaskStatus;
  deadline?: string;
  agent_suggestion?: AgentSuggestionItem;
  remark?: string;
  created_at: string;
  updated_at: string;
}

export interface Visitor extends VisitorBrief {
  status: TaskStatus;
  remark?: string;
  created_at: string;
  updated_at: string;
  requirements: Requirement[];
  tasks: Task[];
}

export interface DashboardSummary {
  total_visitors: number;
  pending_assignment: number;
  assigned: number;
  in_progress: number;
  completed: number;
  exception: number;
  total_tasks: number;
  completed_tasks: number;
}

export interface AgentSuggestionItem {
  task_id: number;
  task_type: RequirementType;
  suggested_assignee_id?: number;
  suggested_assignee_name?: string;
  reason: string;
}

export interface AgentSuggestionResponse {
  agent_name: string;
  suggestions: AgentSuggestionItem[];
  summary: string;
  raw?: Record<string, unknown>;
}

// ─── Agent 协同 ─────────────────────────────

export interface AlertItem {
  task_id: number;
  task_type: RequirementType;
  visitor_name: string;
  assignee_name: string;
  alert_type: "timeout" | "exception" | "pending_too_long" | "info";
  message: string;
}

export interface TrackAlertResponse {
  agent_name: string;
  alerts: AlertItem[];
  summary: string;
}

export interface DailyReportResponse {
  agent_name: string;
  date: string;
  report: string;
  summary_data: DashboardSummary;
}

export interface AgentStatus {
  name: string;
  label: string;
  status: "idle" | "running" | "done" | "error";
  lastResult?: string;
}
