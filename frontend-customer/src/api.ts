import type { VisitorCreate, VisitorOut } from "./types";

export async function createVisitor(payload: VisitorCreate): Promise<VisitorOut> {
  const resp = await fetch("/api/visitors", {
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
