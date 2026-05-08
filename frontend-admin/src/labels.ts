import type { RequirementType, TaskStatus } from "./types";

export const taskTypeLabel: Record<RequirementType, string> = {
  pickup: "接站",
  dropoff: "送站",
  hotel: "住宿",
  meal: "用餐"
};

export const statusLabel: Record<TaskStatus, string> = {
  pending_assignment: "待分配",
  assigned: "已分配",
  in_progress: "进行中",
  completed: "已完成",
  exception: "异常"
};

export const statusColor: Record<TaskStatus, string> = {
  pending_assignment: "gold",
  assigned: "blue",
  in_progress: "cyan",
  completed: "green",
  exception: "red"
};
