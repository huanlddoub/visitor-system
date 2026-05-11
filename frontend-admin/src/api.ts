import type {
  AgentSuggestionResponse,
  DailyReportResponse,
  DashboardSummary,
  Task,
  TaskStatus,
  TrackAlertResponse,
  User,
  Visitor
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || "请求失败");
  }
  return resp.json();
}

export const api = {
  summary: () => request<DashboardSummary>("/api/dashboard/summary"),
  staff: () => request<User[]>("/api/staff"),
  visitors: (status?: string) =>
    request<Visitor[]>(`/api/visitors${status ? `?status=${status}` : ""}`),
  visitor: (id: number) => request<Visitor>(`/api/visitors/${id}`),
  tasks: (params = "") => request<Task[]>(`/api/tasks${params}`),
  myTasks: (assigneeId: number) => request<Task[]>(`/api/tasks/my?assignee_id=${assigneeId}`),
  suggest: (visitorId: number) =>
    request<AgentSuggestionResponse>("/api/agent/assign-suggest", {
      method: "POST",
      body: JSON.stringify({ visitor_id: visitorId })
    }),
  assign: (assignments: { task_id: number; assignee_id: number }[]) =>
    request<Task[]>("/api/tasks/assign", {
      method: "POST",
      body: JSON.stringify({ assignments })
    }),
  updateTask: (taskId: number, status: TaskStatus, remark?: string) =>
    request<Task>(`/api/tasks/${taskId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status, remark })
    }),
  trackAlerts: () =>
    request<TrackAlertResponse>("/api/agent/track-alerts", { method: "POST" }),
  dailyReport: (date?: string) =>
    request<DailyReportResponse>(`/api/agent/daily-report${date ? `?date=${date}` : ""}`, { method: "POST" })
};
