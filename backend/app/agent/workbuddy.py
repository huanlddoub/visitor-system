"""Multi-Agent adapters for WorkBuddy platform."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import requests
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import Settings
from app.models import AgentLog, ReceptionTask, TaskStatus, User, UserRole, Visitor
from app.schemas import (
    AgentSuggestionItem,
    AgentSuggestionResponse,
    TrackAlertResponse,
    AlertItem,
    DailyReportResponse,
)

logger = logging.getLogger(__name__)

TASK_SKILL_WEIGHT = {
    "pickup": "transport",
    "dropoff": "transport",
    "hotel": "hotel",
    "meal": "meal",
}


class WorkBuddyClient:
    """Unified client for calling multiple WorkBuddy Agents."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.workbuddy_base_url
        self.api_key = settings.workbuddy_api_key
        self.timeout = settings.workbuddy_timeout_seconds

    # ─── 通用 Agent 调用方法 ─────────────────────────────

    def _call_agent(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """调用 WorkBuddy 平台上的某个 Agent。"""
        if not self.base_url or not self.api_key or not agent_id:
            return None

        url = f"{self.base_url.rstrip('/')}/agents/{agent_id}/run"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            logger.warning("WorkBuddy Agent [%s] call failed", agent_id, exc_info=True)
            return None

    def _log_agent(
        self, db: Session, agent_name: str, input_data: dict, output_data: dict, reason: str | None = None
    ) -> AgentLog:
        """记录 Agent 调用日志。"""
        log = AgentLog(
            agent_name=agent_name,
            input_payload=input_data,
            output_payload=output_data,
            decision_reason=reason,
        )
        db.add(log)
        db.commit()
        return log

    # ─── Agent 1: 智能分配 ─────────────────────────────

    def suggest_assignment(self, db: Session, visitor_id: int) -> AgentSuggestionResponse:
        tasks = list(
            db.scalars(
                select(ReceptionTask)
                .options(joinedload(ReceptionTask.visitor), joinedload(ReceptionTask.assignee))
                .where(ReceptionTask.visitor_id == visitor_id)
            ).unique()
        )
        if not tasks:
            raise ValueError("visitor has no tasks")

        payload = self._build_assign_payload(db, tasks)
        raw = self._call_agent(self.settings.workbuddy_assign_agent_id, payload)
        response = self._parse_or_fallback_assign(db, tasks, raw)

        self._log_agent(
            db, response.agent_name,
            payload, response.model_dump(mode="json"), response.summary,
        )
        for item in response.suggestions:
            task = next((t for t in tasks if t.id == item.task_id), None)
            if task:
                task.agent_suggestion = item.model_dump(mode="json")
        db.commit()
        return response

    def _build_assign_payload(self, db: Session, tasks: list[ReceptionTask]) -> dict:
        staff = list(db.scalars(select(User).where(User.role == UserRole.receptionist)))
        return {
            "visitor": {
                "id": tasks[0].visitor.id,
                "name": tasks[0].visitor.name,
                "company": tasks[0].visitor.company,
                "visit_time": tasks[0].visitor.visit_time.isoformat(),
                "people_count": tasks[0].visitor.people_count,
            },
            "tasks": [
                {
                    "id": t.id,
                    "type": t.task_type.value,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                    "status": t.status.value,
                }
                for t in tasks
                if t.status == TaskStatus.pending_assignment
            ],
            "staff": [
                {
                    "id": u.id,
                    "name": u.name,
                    "department": u.department,
                    "skills": u.skills or {},
                    "available_status": u.available_status,
                }
                for u in staff
            ],
        }

    def _parse_or_fallback_assign(self, db, tasks, raw) -> AgentSuggestionResponse:
        parsed = self._parse_workbuddy_assign(raw)
        if parsed:
            return AgentSuggestionResponse(
                agent_name="WorkBuddy 智能分配 Agent",
                suggestions=parsed,
                summary="WorkBuddy Agent 返回了分配建议。",
                raw=raw,
            )
        return self._local_fallback_assign(db, tasks, raw)

    def _parse_workbuddy_assign(self, raw) -> list[AgentSuggestionItem]:
        if not raw:
            return []
        data = raw.get("suggestions") or raw.get("data", {}).get("suggestions") or []
        items: list[AgentSuggestionItem] = []
        for item in data:
            try:
                items.append(AgentSuggestionItem(
                    task_id=item["task_id"],
                    task_type=item["task_type"],
                    suggested_assignee_id=item.get("suggested_assignee_id"),
                    suggested_assignee_name=item.get("suggested_assignee_name"),
                    reason=item.get("reason", "WorkBuddy recommendation"),
                ))
            except (KeyError, TypeError, ValueError):
                continue
        return items

    def _local_fallback_assign(self, db, tasks, raw) -> AgentSuggestionResponse:
        staff = list(db.scalars(select(User).where(User.role == UserRole.receptionist)))
        load = {
            row[0]: row[1]
            for row in db.execute(
                select(ReceptionTask.assignee_id, func.count(ReceptionTask.id))
                .where(ReceptionTask.assignee_id.is_not(None))
                .group_by(ReceptionTask.assignee_id)
            ).all()
        }
        suggestions: list[AgentSuggestionItem] = []
        for task in tasks:
            skill_key = TASK_SKILL_WEIGHT.get(task.task_type.value, task.task_type.value)
            candidates = sorted(
                staff,
                key=lambda u: (
                    0 if (u.skills or {}).get(skill_key) or (u.skills or {}).get(task.task_type.value) else 1,
                    0 if u.available_status == "available" else 1,
                    load.get(u.id, 0),
                    u.id,
                ),
            )
            assignee = candidates[0] if candidates else None
            suggestions.append(AgentSuggestionItem(
                task_id=task.id,
                task_type=task.task_type,
                suggested_assignee_id=assignee.id if assignee else None,
                suggested_assignee_name=assignee.name if assignee else None,
                reason="Local fallback: 匹配技能、可用性和当前负载。",
            ))
        return AgentSuggestionResponse(
            agent_name="智能分配 Agent (本地回退)",
            suggestions=suggestions,
            summary="WorkBuddy 未配置或不可用，本地规则生成演示建议。",
            raw=raw,
        )

    # ─── Agent 2: 进度跟踪与告警 ─────────────────────────────

    def track_alerts(self, db: Session) -> TrackAlertResponse:
        """扫描所有任务，检测超时和异常，生成告警。"""
        now = datetime.utcnow()
        tasks = list(db.scalars(
            select(ReceptionTask)
            .options(joinedload(ReceptionTask.visitor), joinedload(ReceptionTask.assignee))
        ).unique())

        alerts: list[AlertItem] = []

        for task in tasks:
            # 超时检测：已分配但超过 deadline 2 小时仍未开始
            if task.status == TaskStatus.assigned and task.deadline:
                if now > task.deadline + timedelta(hours=2):
                    alerts.append(AlertItem(
                        task_id=task.id,
                        task_type=task.task_type,
                        visitor_name=task.visitor.name if task.visitor else f"#{task.visitor_id}",
                        assignee_name=task.assignee.name if task.assignee else "未分配",
                        alert_type="timeout",
                        message=f"任务 #{task.id}（{task.task_type.value}）已超过截止时间 2 小时仍未开始执行。",
                    ))

            # 异常标记检测
            if task.status == TaskStatus.exception:
                alerts.append(AlertItem(
                    task_id=task.id,
                    task_type=task.task_type,
                    visitor_name=task.visitor.name if task.visitor else f"#{task.visitor_id}",
                    assignee_name=task.assignee.name if task.assignee else "未分配",
                    alert_type="exception",
                    message=f"任务 #{task.id}（{task.task_type.value}）状态异常，需要关注。",
                ))

            # 待分配过久：超过 4 小时仍待分配
            if task.status == TaskStatus.pending_assignment:
                if task.created_at and now > task.created_at + timedelta(hours=4):
                    alerts.append(AlertItem(
                        task_id=task.id,
                        task_type=task.task_type,
                        visitor_name=task.visitor.name if task.visitor else f"#{task.visitor_id}",
                        assignee_name="未分配",
                        alert_type="pending_too_long",
                        message=f"任务 #{task.id}（{task.task_type.value}）已待分配超过 4 小时。",
                    ))

        # 尝试调用 WorkBuddy 进度跟踪 Agent 获取更智能的告警建议
        payload = {
            "total_tasks": len(tasks),
            "alerts_count": len(alerts),
            "alerts": [a.model_dump() for a in alerts],
            "timestamp": now.isoformat(),
        }
        raw = self._call_agent(self.settings.workbuddy_track_agent_id, payload)

        if raw:
            # 如果 Agent 返回了额外告警或建议，合并进来
            extra = raw.get("extra_alerts") or []
            for item in extra:
                try:
                    alerts.append(AlertItem(
                        task_id=item.get("task_id", 0),
                        task_type=item.get("task_type", "pickup"),
                        visitor_name=item.get("visitor_name", ""),
                        assignee_name=item.get("assignee_name", ""),
                        alert_type=item.get("alert_type", "info"),
                        message=item.get("message", ""),
                    ))
                except (KeyError, TypeError, ValueError):
                    continue

        response = TrackAlertResponse(
            agent_name="进度跟踪 Agent",
            alerts=alerts,
            summary=f"共扫描 {len(tasks)} 个任务，发现 {len(alerts)} 条告警。",
            raw=raw,
        )

        self._log_agent(db, response.agent_name, payload, response.model_dump(mode="json"), response.summary)
        return response

    # ─── Agent 3: 日报汇报 ─────────────────────────────

    def daily_report(self, db: Session, date: str | None = None) -> DailyReportResponse:
        """生成接待日报。"""
        from app.services import get_dashboard_summary
        summary = get_dashboard_summary(db)

        # 获取已完成任务
        today = date or datetime.utcnow().strftime("%Y-%m-%d")
        completed_tasks = list(db.scalars(
            select(ReceptionTask)
            .options(joinedload(ReceptionTask.visitor), joinedload(ReceptionTask.assignee))
            .where(ReceptionTask.status == TaskStatus.completed)
        ).unique())

        completed_details = [
            {
                "task_id": t.id,
                "task_type": t.task_type.value,
                "visitor_name": t.visitor.name if t.visitor else f"#{t.visitor_id}",
                "assignee_name": t.assignee.name if t.assignee else "未分配",
            }
            for t in completed_tasks
        ]

        payload = {
            "date": today,
            "summary": summary.model_dump(),
            "completed_tasks": completed_details,
            "pending_count": summary.pending_assignment,
            "exception_count": summary.exception,
        }

        raw = self._call_agent(self.settings.workbuddy_report_agent_id, payload)

        # 生成本地回退报告
        report_text = self._generate_local_report(today, summary, completed_details)
        agent_name = "汇报总结 Agent (本地回退)"

        if raw and raw.get("report"):
            report_text = raw["report"]
            agent_name = "汇报总结 Agent"

        response = DailyReportResponse(
            agent_name=agent_name,
            date=today,
            report=report_text,
            summary_data=summary.model_dump(),
            raw=raw,
        )

        self._log_agent(db, response.agent_name, payload, response.model_dump(mode="json"))
        return response

    def _generate_local_report(self, date: str, summary, completed_details) -> str:
        lines = [
            f"# 客户接待日报 — {date}",
            "",
            "## 核心数据",
            f"- 总客户数：{summary.total_visitors}",
            f"- 待分配：{summary.pending_assignment}",
            f"- 已分配：{summary.assigned}",
            f"- 进行中：{summary.in_progress}",
            f"- 已完成：{summary.completed}",
            f"- 异常：{summary.exception}",
            f"- 任务完成率：{round(summary.completed_tasks / max(summary.total_tasks, 1) * 100, 1)}%",
            "",
            "## 已完成任务明细",
        ]
        if completed_details:
            for item in completed_details:
                lines.append(f"- 任务#{item['task_id']} {item['task_type']} | 客户：{item['visitor_name']} | 负责人：{item['assignee_name']}")
        else:
            lines.append("- 暂无已完成任务")
        lines.append("")
        lines.append("## 待处理事项")
        if summary.pending_assignment > 0:
            lines.append(f"- ⚠️ 有 {summary.pending_assignment} 位客户待分配接待人员，请尽快处理。")
        if summary.exception > 0:
            lines.append(f"- 🔴 有 {summary.exception} 个异常任务需要关注。")
        if summary.pending_assignment == 0 and summary.exception == 0:
            lines.append("- 当前无待处理事项。")
        return "\n".join(lines)
