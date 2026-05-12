import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    receptionist = "receptionist"


class VisitorStatus(str, enum.Enum):
    pending_assignment = "pending_assignment"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    exception = "exception"


class RequirementType(str, enum.Enum):
    general = "general"
    pickup = "pickup"
    dropoff = "dropoff"
    hotel = "hotel"
    meal = "meal"


class TaskStatus(str, enum.Enum):
    pending_assignment = "pending_assignment"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    exception = "exception"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    department: Mapped[str | None] = mapped_column(String(64))
    skills: Mapped[dict | None] = mapped_column(JSON)
    available_status: Mapped[str] = mapped_column(String(32), default="available")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    tasks: Mapped[list["ReceptionTask"]] = relationship(back_populates="assignee")


class Visitor(Base):
    __tablename__ = "visitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    company: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    visit_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    people_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[VisitorStatus] = mapped_column(
        Enum(VisitorStatus), default=VisitorStatus.pending_assignment, nullable=False
    )
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    requirements: Mapped[list["VisitorRequirement"]] = relationship(
        back_populates="visitor", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["ReceptionTask"]] = relationship(
        back_populates="visitor", cascade="all, delete-orphan"
    )


class VisitorRequirement(Base):
    __tablename__ = "visitor_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visitor_id: Mapped[int] = mapped_column(ForeignKey("visitors.id"), nullable=False)
    type: Mapped[RequirementType] = mapped_column(Enum(RequirementType), nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.pending_assignment, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    visitor: Mapped[Visitor] = relationship(back_populates="requirements")
    task: Mapped["ReceptionTask"] = relationship(back_populates="requirement")


class ReceptionTask(Base):
    __tablename__ = "reception_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    visitor_id: Mapped[int] = mapped_column(ForeignKey("visitors.id"), nullable=False)
    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("visitor_requirements.id"), nullable=False, unique=True
    )
    task_type: Mapped[RequirementType] = mapped_column(Enum(RequirementType), nullable=False)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.pending_assignment, nullable=False
    )
    deadline: Mapped[datetime | None] = mapped_column(DateTime)
    agent_suggestion: Mapped[dict | None] = mapped_column(JSON)
    remark: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    visitor: Mapped[Visitor] = relationship(back_populates="tasks")
    requirement: Mapped[VisitorRequirement] = relationship(back_populates="task")
    assignee: Mapped[User | None] = relationship(back_populates="tasks")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent_name: Mapped[str] = mapped_column(String(80), nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
