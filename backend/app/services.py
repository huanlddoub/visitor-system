from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    ReceptionTask,
    RequirementType,
    TaskStatus,
    User,
    UserRole,
    Visitor,
    VisitorRequirement,
    VisitorStatus,
)
from app.schemas import DashboardSummary, VisitorCreate


def sync_visitor_status(db: Session, visitor_id: int) -> None:
    tasks = db.scalars(
        select(ReceptionTask).where(ReceptionTask.visitor_id == visitor_id)
    ).all()
    visitor = db.get(Visitor, visitor_id)
    if not visitor or not tasks:
        return

    statuses = {task.status for task in tasks}
    if TaskStatus.exception in statuses:
        visitor.status = VisitorStatus.exception
    elif statuses == {TaskStatus.completed}:
        visitor.status = VisitorStatus.completed
    elif TaskStatus.in_progress in statuses:
        visitor.status = VisitorStatus.in_progress
    elif TaskStatus.pending_assignment in statuses:
        visitor.status = VisitorStatus.pending_assignment
    else:
        visitor.status = VisitorStatus.assigned


def create_visitor(db: Session, payload: VisitorCreate) -> Visitor:
    visitor = Visitor(
        name=payload.name,
        company=payload.company,
        phone=payload.phone,
        visit_time=payload.visit_time,
        people_count=payload.people_count,
        remark=payload.remark,
    )
    db.add(visitor)
    db.flush()

    for item in payload.requirements:
        requirement = VisitorRequirement(
            visitor_id=visitor.id,
            type=item.type,
            detail=item.detail,
        )
        db.add(requirement)
        db.flush()
        db.add(
            ReceptionTask(
                visitor_id=visitor.id,
                requirement_id=requirement.id,
                task_type=item.type,
                deadline=payload.visit_time,
            )
        )

    db.commit()
    return get_visitor(db, visitor.id)


def get_visitor(db: Session, visitor_id: int) -> Visitor:
    visitor = db.execute(
        select(Visitor)
        .options(
            joinedload(Visitor.requirements),
            joinedload(Visitor.tasks).joinedload(ReceptionTask.assignee),
        )
        .where(Visitor.id == visitor_id)
    ).unique().scalar_one_or_none()
    if not visitor:
        raise ValueError("visitor not found")
    return visitor


def list_visitors(
    db: Session, status: VisitorStatus | None = None, keyword: str | None = None
) -> list[Visitor]:
    stmt = select(Visitor).options(
        joinedload(Visitor.requirements),
        joinedload(Visitor.tasks).joinedload(ReceptionTask.assignee),
    )
    if status:
        stmt = stmt.where(Visitor.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where((Visitor.name.like(like)) | (Visitor.company.like(like)))
    return list(db.scalars(stmt.order_by(Visitor.created_at.desc())).unique())


def list_tasks(
    db: Session,
    status: TaskStatus | None = None,
    assignee_id: int | None = None,
    task_type: RequirementType | None = None,
) -> list[ReceptionTask]:
    stmt = select(ReceptionTask).options(
        joinedload(ReceptionTask.assignee),
        joinedload(ReceptionTask.visitor),
    )
    if status:
        stmt = stmt.where(ReceptionTask.status == status)
    if assignee_id:
        stmt = stmt.where(ReceptionTask.assignee_id == assignee_id)
    if task_type:
        stmt = stmt.where(ReceptionTask.task_type == task_type)
    return list(db.scalars(stmt.order_by(ReceptionTask.created_at.desc())).unique())


def assign_tasks(db: Session, assignments: dict[int, int]) -> list[ReceptionTask]:
    tasks = db.scalars(
        select(ReceptionTask).where(ReceptionTask.id.in_(assignments.keys()))
    ).all()
    found_ids = {task.id for task in tasks}
    missing = set(assignments) - found_ids
    if missing:
        raise ValueError(f"tasks not found: {sorted(missing)}")

    for task in tasks:
        if not db.get(User, assignments[task.id]):
            raise ValueError(f"assignee not found: {assignments[task.id]}")
        task.assignee_id = assignments[task.id]
        task.status = TaskStatus.assigned
        task.requirement.status = TaskStatus.assigned

    visitor_ids = {task.visitor_id for task in tasks}
    for visitor_id in visitor_ids:
        sync_visitor_status(db, visitor_id)

    db.commit()
    return list_tasks(db)


def update_task_status(
    db: Session, task_id: int, status: TaskStatus, remark: str | None
) -> ReceptionTask:
    task = db.scalar(
        select(ReceptionTask)
        .options(joinedload(ReceptionTask.requirement), joinedload(ReceptionTask.assignee))
        .options(joinedload(ReceptionTask.visitor))
        .where(ReceptionTask.id == task_id)
    )
    if not task:
        raise ValueError("task not found")
    task.status = status
    task.requirement.status = status
    if remark is not None:
        task.remark = remark
    sync_visitor_status(db, task.visitor_id)
    db.commit()
    return task


def get_dashboard_summary(db: Session) -> DashboardSummary:
    def count_visitors(status: VisitorStatus | None = None) -> int:
        stmt = select(func.count(Visitor.id))
        if status:
            stmt = stmt.where(Visitor.status == status)
        return int(db.scalar(stmt) or 0)

    total_tasks = int(db.scalar(select(func.count(ReceptionTask.id))) or 0)
    completed_tasks = int(
        db.scalar(
            select(func.count(ReceptionTask.id)).where(
                ReceptionTask.status == TaskStatus.completed
            )
        )
        or 0
    )

    return DashboardSummary(
        total_visitors=count_visitors(),
        pending_assignment=count_visitors(VisitorStatus.pending_assignment),
        assigned=count_visitors(VisitorStatus.assigned),
        in_progress=count_visitors(VisitorStatus.in_progress),
        completed=count_visitors(VisitorStatus.completed),
        exception=count_visitors(VisitorStatus.exception),
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
    )


def list_receptionists(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(User.role == UserRole.receptionist)
            .order_by(User.department, User.id)
        )
    )
