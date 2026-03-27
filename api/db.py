"""Database setup and repository helpers."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from api.models import AgentRecord, AssessmentJobRecord, Base, InputAssetRecord, ReportRecord

_ENGINE = None
_SESSION_FACTORY = None


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def get_database_url() -> str:
    raw = (os.getenv("DATABASE_URL") or "").strip()
    if raw:
        return _normalize_database_url(raw)
    return f"sqlite+pysqlite:///{Path('integrapilot.db').resolve().as_posix()}"


def get_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(get_database_url(), future=True)
    return _ENGINE


def get_session_factory():
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SESSION_FACTORY


@contextmanager
def session_scope():
    sess: Session = get_session_factory()()
    try:
        yield sess
        sess.commit()
    except Exception:
        sess.rollback()
        raise
    finally:
        sess.close()


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def run_migrations() -> None:
    """Run Alembic migrations if available, otherwise fallback to create_all."""
    wait_seconds = max(1, int(os.getenv("DB_CONNECT_WAIT_SEC", "25")))
    deadline = time.time() + wait_seconds

    def _run_once() -> None:
        try:
            from alembic import command
            from alembic.config import Config
        except Exception:
            init_db()
            return

        cfg_path = Path(__file__).resolve().parent.parent / "alembic.ini"
        if not cfg_path.exists():
            init_db()
            return
        cfg = Config(str(cfg_path))
        cfg.set_main_option("sqlalchemy.url", get_database_url())
        managed_tables = {"agents", "reports", "assessment_jobs", "input_assets"}
        with get_engine().connect() as conn:
            insp = inspect(conn)
            has_version_table = insp.has_table("alembic_version")
            existing_tables = set(insp.get_table_names())
        if not has_version_table and managed_tables.intersection(existing_tables):
            command.stamp(cfg, "head")
            return
        command.upgrade(cfg, "head")

    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            _run_once()
            return
        except OperationalError as e:
            last_error = e
            time.sleep(1)
    if last_error:
        raise last_error

    _run_once()


def detect_input_mode(path_a: str, path_b: str) -> str:
    a_is_file = Path(path_a).is_file()
    b_is_file = Path(path_b).is_file()
    if a_is_file and b_is_file:
        return "file_vs_file"
    if a_is_file or b_is_file:
        return "file_vs_dir"
    return "dir_vs_dir"


def upsert_default_agent(now: datetime, default_item: dict[str, str]) -> None:
    with session_scope() as sess:
        existing = sess.get(AgentRecord, default_item["id"])
        if existing:
            return
        sess.add(
            AgentRecord(
                id=default_item["id"],
                name=default_item["name"],
                role=default_item["role"],
                goal=default_item["goal"],
                backstory=default_item["backstory"],
                model=(default_item.get("model") or "").strip() or None,
                is_default=True,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )


def list_agents() -> list[dict[str, str]]:
    with session_scope() as sess:
        rows = sess.execute(
            select(AgentRecord).where(AgentRecord.is_active.is_(True)).order_by(AgentRecord.created_at.asc())
        ).scalars()
        out: list[dict[str, str]] = []
        for x in rows:
            out.append(
                {
                    "id": x.id,
                    "name": x.name,
                    "role": x.role,
                    "goal": x.goal,
                    "backstory": x.backstory,
                    "model": x.model or "",
                }
            )
        return out


def create_agent(name: str, role: str, goal: str, backstory: str, model: str | None, now: datetime) -> dict[str, str]:
    agent_id = f"custom-{uuid4().hex[:8]}"
    with session_scope() as sess:
        row = AgentRecord(
            id=agent_id,
            name=name,
            role=role,
            goal=goal,
            backstory=backstory,
            model=(model or "").strip() or None,
            is_default=False,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        sess.add(row)
    return {
        "id": agent_id,
        "name": name,
        "role": role,
        "goal": goal,
        "backstory": backstory,
        "model": (model or "").strip(),
    }


def deactivate_agent(agent_id: str, now: datetime) -> bool:
    with session_scope() as sess:
        row = sess.get(AgentRecord, agent_id)
        if not row or not row.is_active:
            return False
        row.is_active = False
        row.updated_at = now
        sess.add(row)
        return True


def get_agent(agent_id: str) -> dict[str, str] | None:
    with session_scope() as sess:
        row = sess.get(AgentRecord, agent_id)
        if not row or not row.is_active:
            return None
        return {
            "id": row.id,
            "name": row.name,
            "role": row.role,
            "goal": row.goal,
            "backstory": row.backstory,
            "model": row.model or "",
        }


def create_job(path_a: str, path_b: str, input_mode: str, now: datetime) -> str:
    job_id = uuid4().hex
    with session_scope() as sess:
        sess.add(
            AssessmentJobRecord(
                id=job_id,
                project_a_path=path_a,
                project_b_path=path_b,
                input_mode=input_mode,
                status="running",
                started_at=now,
            )
        )
    return job_id


def complete_job(job_id: str, report_id: str, status: str, now: datetime, error_message: str | None = None) -> None:
    with session_scope() as sess:
        row = sess.get(AssessmentJobRecord, job_id)
        if not row:
            return
        row.status = status
        row.finished_at = now
        row.error_message = error_message
        row.report_id = report_id
        row.duration_ms = int((now - row.started_at).total_seconds() * 1000)
        sess.add(row)


def fail_job(job_id: str, now: datetime, error_message: str) -> None:
    with session_scope() as sess:
        row = sess.get(AssessmentJobRecord, job_id)
        if not row:
            return
        row.status = "failed"
        row.finished_at = now
        row.error_message = error_message
        row.duration_ms = int((now - row.started_at).total_seconds() * 1000)
        sess.add(row)


def upsert_report(
    report_id: str,
    report_name: str,
    file_path: str,
    project_a_path: str,
    project_b_path: str,
    input_mode: str,
    size_bytes: int,
    now: datetime,
) -> None:
    with session_scope() as sess:
        row = sess.get(ReportRecord, report_id)
        if row is None:
            row = ReportRecord(
                id=report_id,
                report_name=report_name,
                file_path=file_path,
                project_a_path=project_a_path,
                project_b_path=project_b_path,
                input_mode=input_mode,
                status="completed",
                created_at=now,
                updated_at=now,
                size_bytes=size_bytes,
            )
        else:
            row.report_name = report_name
            row.file_path = file_path
            row.project_a_path = project_a_path
            row.project_b_path = project_b_path
            row.input_mode = input_mode
            row.status = "completed"
            row.updated_at = now
            row.size_bytes = size_bytes
        sess.add(row)


def list_reports() -> list[dict[str, object]]:
    with session_scope() as sess:
        rows = sess.execute(select(ReportRecord).order_by(ReportRecord.updated_at.desc())).scalars()
        return [
            {
                "id": r.id,
                "name": r.report_name,
                "file_path": r.file_path,
                "updated_at": r.updated_at,
                "size": r.size_bytes,
            }
            for r in rows
        ]


def get_report(report_id: str) -> dict[str, object] | None:
    with session_scope() as sess:
        r = sess.get(ReportRecord, report_id)
        if not r:
            return None
        return {
            "id": r.id,
            "name": r.report_name,
            "file_path": r.file_path,
            "project_a_path": r.project_a_path,
            "project_b_path": r.project_b_path,
            "input_mode": r.input_mode,
            "updated_at": r.updated_at,
            "size": r.size_bytes,
        }


def create_input_asset(
    slot: str,
    source_type: str,
    resolved_path: str,
    now: datetime,
    upload_id: str | None = None,
    origin_url: str | None = None,
    branch: str | None = None,
    size_bytes: int | None = None,
) -> str:
    asset_id = uuid4().hex
    with session_scope() as sess:
        sess.add(
            InputAssetRecord(
                id=asset_id,
                slot=slot,
                source_type=source_type,
                upload_id=upload_id,
                origin_url=origin_url,
                branch=branch,
                resolved_path=resolved_path,
                size_bytes=size_bytes,
                created_at=now,
            )
        )
    return asset_id
