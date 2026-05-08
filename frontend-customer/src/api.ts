import type { VisitorCreate, VisitorOut } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function createVisitor(payload: VisitorCreate): Promise<VisitorOut> {
  const resp = await fetch(`${API_BASE}/api/visitors`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || "提交失败");
  }
  return resp.json();
}
