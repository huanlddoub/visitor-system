from collections.abc import Generator
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Settings(BaseSettings):
    app_name: str = "Visitor Reception Assistant"
    database_url: str = (
        "mysql+pymysql://root:password@127.0.0.1:3306/"
        "visitor_system?charset=utf8mb4"
    )
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    # --- WorkBuddy 多 Agent 配置 ---
    workbuddy_base_url: str | None = None
    workbuddy_api_key: str | None = None
    workbuddy_timeout_seconds: int = 15

    # 4 个 Agent ID（在 WorkBuddy 平台创建后填入）
    workbuddy_collect_agent_id: str | None = None      # 信息收集 Agent
    workbuddy_assign_agent_id: str | None = None       # 智能分配 Agent
    workbuddy_track_agent_id: str | None = None        # 进度跟踪 Agent
    workbuddy_report_agent_id: str | None = None       # 汇报总结 Agent

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_database_exists(database_url: str) -> None:
    url = make_url(database_url)
    if not url.drivername.startswith("mysql") or not url.database:
        return

    database_name = url.database
    if not database_name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe database name: {database_name}")

    server_url = url.set(database="")
    bootstrap_engine = create_engine(server_url, pool_pre_ping=True)
    try:
        with bootstrap_engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{database_name}` "
                    "DEFAULT CHARACTER SET utf8mb4 "
                    "DEFAULT COLLATE utf8mb4_unicode_ci"
                )
            )
    finally:
        bootstrap_engine.dispose()


class Base(DeclarativeBase):
    pass


settings = get_settings()
ensure_database_exists(settings.database_url)
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
