from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import RequirementType, TaskStatus, UserRole, VisitorStatus


class UserOut(BaseModel):
    id: int
    name: str
    phone: str | None = None
    role: UserRole
    department: str | None = None
    skills: dict[str, Any] | None = None
    available_status: str

    model_config = ConfigDict(from_attributes=True)


class RequirementCreate(BaseModel):
    type: RequirementType
    detail: dict[str, Any] = Field(default_factory=dict)


class RequirementOut(BaseModel):
    id: int
    type: RequirementType
    detail: dict[str, Any]
    status: TaskStatus

    model_config = ConfigDict(from_attributes=True)


class VisitorBrief(BaseModel):
    id: int
    name: str
    company: str
    phone: str
    visit_time: datetime
    people_count: int

    model_config = ConfigDict(from_attributes=True)


class VisitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    company: str = Field(min_length=1, max_length=128)
    phone: str = Field(min_length=1, max_length=32)
    visit_time: datetime
    people_count: int = Field(gt=0, le=500)
    remark: str | None = None
    requirements: list[RequirementCreate] = Field(default_factory=list)


class TaskOut(BaseModel):
    id: int
    visitor_id: int
    requirement_id: int
    task_type: RequirementType
    visitor: VisitorBrief | None = None
    assignee_id: int | None = None
    assignee: UserOut | None = None
    status: TaskStatus
    deadline: datetime | None = None
    agent_suggestion: dict[str, Any] | None = None
    remark: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VisitorOut(BaseModel):
    id: int
    name: str
    company: str
    phone: str
    visit_time: datetime
    people_count: int
    status: VisitorStatus
    remark: str | None = None
    created_at: datetime
    updated_at: datetime
    requirements: list[RequirementOut] = []
    tasks: list[TaskOut] = []

    model_config = ConfigDict(from_attributes=True)


class AssignmentItem(BaseModel):
    task_id: int
    assignee_id: int


class AssignTasksRequest(BaseModel):
    assignments: list[AssignmentItem] = Field(min_length=1)


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    remark: str | None = None


class DashboardSummary(BaseModel):
    total_visitors: int
    pending_assignment: int
    assigned: int
    in_progress: int
    completed: int
    exception: int
    total_tasks: int
    completed_tasks: int


class AgentSuggestionRequest(BaseModel):
    visitor_id: int


class AgentSuggestionItem(BaseModel):
    task_id: int
    task_type: RequirementType
    suggested_assignee_id: int | None = None
    suggested_assignee_name: str | None = None
    reason: str


class AgentSuggestionResponse(BaseModel):
    agent_name: str
    suggestions: list[AgentSuggestionItem]
    summary: str
    raw: dict[str, Any] | None = None
