from __future__ import annotations

import logging
from typing import Any

import requests
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import Settings
from app.models import AgentLog, ReceptionTask, TaskStatus, User, UserRole
from app.schemas import AgentSuggestionItem, AgentSuggestionResponse

logger = logging.getLogger(__name__)

TASK_SKILL_WEIGHT = {
    "pickup": "transport",
    "dropoff": "transport",
    "hotel": "hotel",
    "meal": "meal",
}


class WorkBuddyClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def suggest_assignment(
        self, db: Session, visitor_id: int
    ) -> AgentSuggestionResponse:
        tasks = list(
            db.scalars(
                select(ReceptionTask)
                .options(joinedload(ReceptionTask.visitor), joinedload(ReceptionTask.assignee))
                .where(ReceptionTask.visitor_id == visitor_id)
            ).unique()
        )
        if not tasks:
            raise ValueError("visitor has no tasks")

        payload = self._build_payload(db, tasks)
        raw = self._call_workbuddy(payload)
        response = self._parse_or_fallback(db, tasks, raw)

        log = AgentLog(
            agent_name=response.agent_name,
            input_payload=payload,
            output_payload=response.model_dump(mode="json"),
            decision_reason=response.summary,
        )
        db.add(log)
        for item in response.suggestions:
            task = next((task for task in tasks if task.id == item.task_id), None)
            if task:
                task.agent_suggestion = item.model_dump(mode="json")
        db.commit()
        return response

    def _build_payload(self, db: Session, tasks: list[ReceptionTask]) -> dict[str, Any]:
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
                    "id": task.id,
                    "type": task.task_type.value,
                    "deadline": task.deadline.isoformat() if task.deadline else None,
                    "status": task.status.value,
                }
                for task in tasks
                if task.status == TaskStatus.pending_assignment
            ],
            "staff": [
                {
                    "id": user.id,
                    "name": user.name,
                    "department": user.department,
                    "skills": user.skills or {},
                    "available_status": user.available_status,
                }
                for user in staff
            ],
        }

    def _call_workbuddy(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not (
            self.settings.workbuddy_base_url
            and self.settings.workbuddy_api_key
            and self.settings.workbuddy_assign_agent_id
        ):
            return None

        url = (
            f"{self.settings.workbuddy_base_url.rstrip('/')}/agents/"
            f"{self.settings.workbuddy_assign_agent_id}/run"
        )
        headers = {"Authorization": f"Bearer {self.settings.workbuddy_api_key}"}
        try:
            resp = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.settings.workbuddy_timeout_seconds,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            logger.warning("WorkBuddy call failed; using local fallback", exc_info=True)
            return None

    def _parse_or_fallback(
        self,
        db: Session,
        tasks: list[ReceptionTask],
        raw: dict[str, Any] | None,
    ) -> AgentSuggestionResponse:
        parsed = self._parse_workbuddy_response(raw)
        if parsed:
            return AgentSuggestionResponse(
                agent_name="WorkBuddy Assignment Agent",
                suggestions=parsed,
                summary="WorkBuddy returned assignment suggestions.",
                raw=raw,
            )
        return self._local_fallback(db, tasks, raw)

    def _parse_workbuddy_response(
        self, raw: dict[str, Any] | None
    ) -> list[AgentSuggestionItem]:
        if not raw:
            return []
        data = raw.get("suggestions") or raw.get("data", {}).get("suggestions") or []
        suggestions: list[AgentSuggestionItem] = []
        for item in data:
            try:
                suggestions.append(
                    AgentSuggestionItem(
                        task_id=item["task_id"],
                        task_type=item["task_type"],
                        suggested_assignee_id=item.get("suggested_assignee_id"),
                        suggested_assignee_name=item.get("suggested_assignee_name"),
                        reason=item.get("reason", "WorkBuddy recommendation"),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return suggestions

    def _local_fallback(
        self,
        db: Session,
        tasks: list[ReceptionTask],
        raw: dict[str, Any] | None,
    ) -> AgentSuggestionResponse:
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
                key=lambda user: (
                    0
                    if (user.skills or {}).get(skill_key)
                    or (user.skills or {}).get(task.task_type.value)
                    else 1,
                    0 if user.available_status == "available" else 1,
                    load.get(user.id, 0),
                    user.id,
                ),
            )
            assignee = candidates[0] if candidates else None
            reason = "Local fallback: matched task skill, availability, and current load."
            suggestions.append(
                AgentSuggestionItem(
                    task_id=task.id,
                    task_type=task.task_type,
                    suggested_assignee_id=assignee.id if assignee else None,
                    suggested_assignee_name=assignee.name if assignee else None,
                    reason=reason,
                )
            )

        return AgentSuggestionResponse(
            agent_name="WorkBuddy Assignment Agent (local fallback)",
            suggestions=suggestions,
            summary="WorkBuddy is not configured or unavailable; local rules produced demo-ready suggestions.",
            raw=raw,
        )
