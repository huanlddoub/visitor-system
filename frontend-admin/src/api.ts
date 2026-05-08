import type {
  AgentSuggestionResponse,
  DashboardSummary,
  Task,
  TaskStatus,
  User,
  Visitor
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE}${path}`, {
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
    })
};
