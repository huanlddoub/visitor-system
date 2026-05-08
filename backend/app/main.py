from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.agent.workbuddy import WorkBuddyClient
from app.database import Base, SessionLocal, engine, get_db, get_settings
from app.models import RequirementType, TaskStatus, User, UserRole, VisitorStatus
from app.schemas import (
    AgentSuggestionRequest,
    AgentSuggestionResponse,
    AlertItem,
    AssignTasksRequest,
    DailyReportResponse,
    DashboardSummary,
    TaskOut,
    TaskStatusUpdate,
    TrackAlertResponse,
    UserOut,
    VisitorCreate,
    VisitorOut,
)
from app.services import (
    assign_tasks,
    create_visitor,
    get_dashboard_summary,
    get_visitor,
    list_receptionists,
    list_tasks,
    list_visitors,
    update_task_status,
)

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed_demo_staff()


def seed_demo_staff() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.role == UserRole.receptionist).count() > 0:
            return
        db.add_all(
            [
                User(
                    name="张敏",
                    phone="13800000001",
                    role=UserRole.receptionist,
                    department="综合接待",
                    skills={"transport": True, "pickup": True, "dropoff": True},
                    available_status="available",
                ),
                User(
                    name="李航",
                    phone="13800000002",
                    role=UserRole.receptionist,
                    department="行政保障",
                    skills={"hotel": True, "meal": True},
                    available_status="available",
                ),
                User(
                    name="王悦",
                    phone="13800000003",
                    role=UserRole.receptionist,
                    department="会务服务",
                    skills={"meal": True, "transport": True},
                    available_status="busy",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/staff", response_model=list[UserOut])
def staff(db: Session = Depends(get_db)) -> list[User]:
    return list_receptionists(db)


@app.post("/api/visitors", response_model=VisitorOut)
def create_visitor_endpoint(
    payload: VisitorCreate, db: Session = Depends(get_db)
) -> VisitorOut:
    return create_visitor(db, payload)


@app.get("/api/visitors", response_model=list[VisitorOut])
def visitors(
    status: VisitorStatus | None = None,
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[VisitorOut]:
    return list_visitors(db, status, keyword)


@app.get("/api/visitors/{visitor_id}", response_model=VisitorOut)
def visitor_detail(visitor_id: int, db: Session = Depends(get_db)) -> VisitorOut:
    try:
        return get_visitor(db, visitor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/tasks", response_model=list[TaskOut])
def tasks(
    status: TaskStatus | None = None,
    assignee_id: int | None = None,
    task_type: RequirementType | None = None,
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    return list_tasks(db, status, assignee_id, task_type)


@app.get("/api/tasks/my", response_model=list[TaskOut])
def my_tasks(assignee_id: int, db: Session = Depends(get_db)) -> list[TaskOut]:
    return list_tasks(db, assignee_id=assignee_id)


@app.post("/api/tasks/assign", response_model=list[TaskOut])
def assign_tasks_endpoint(
    payload: AssignTasksRequest, db: Session = Depends(get_db)
) -> list[TaskOut]:
    try:
        assignments = {item.task_id: item.assignee_id for item in payload.assignments}
        return assign_tasks(db, assignments)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/tasks/{task_id}/status", response_model=TaskOut)
def update_task_status_endpoint(
    task_id: int, payload: TaskStatusUpdate, db: Session = Depends(get_db)
) -> TaskOut:
    try:
        return update_task_status(db, task_id, payload.status, payload.remark)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    return get_dashboard_summary(db)


@app.post("/api/agent/assign-suggest", response_model=AgentSuggestionResponse)
def agent_assign_suggest(
    payload: AgentSuggestionRequest, db: Session = Depends(get_db)
) -> AgentSuggestionResponse:
    try:
        return WorkBuddyClient(settings).suggest_assignment(db, payload.visitor_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/agent/track-alerts", response_model=TrackAlertResponse)
def agent_track_alerts(db: Session = Depends(get_db)) -> TrackAlertResponse:
    """Agent 3: 进度跟踪 — 扫描超时/异常任务并生成告警。"""
    return WorkBuddyClient(settings).track_alerts(db)


@app.post("/api/agent/daily-report", response_model=DailyReportResponse)
def agent_daily_report(
    date: str | None = None, db: Session = Depends(get_db)
) -> DailyReportResponse:
    """Agent 4: 日报汇报 — 生成接待日报和数据洞察。"""
    return WorkBuddyClient(settings).daily_report(db, date)
