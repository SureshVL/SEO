from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import sqlite3
from typing import Any
from uuid import uuid4

from app.schemas.research import WorkflowResponse


@dataclass
class JobRecord:
    job_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    payload: dict[str, Any]
    result: WorkflowResponse | None = None
    error: str | None = None
    logs: list[dict[str, Any]] | None = None


class SQLiteJobStore:
    def __init__(self, path: str):
        self.path = path
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                create table if not exists jobs (
                    job_id text primary key,
                    status text not null,
                    created_at text not null,
                    updated_at text not null,
                    payload text not null,
                    result text,
                    error text
                )
                """
            )
            conn.execute(
                """
                create table if not exists job_logs (
                    job_id text not null,
                    seq integer not null,
                    at text not null,
                    level text not null,
                    message text not null,
                    primary key (job_id, seq)
                )
                """
            )

    def create_job(self, payload: dict[str, Any]) -> JobRecord:
        now = datetime.now(timezone.utc)
        job_id = str(uuid4())
        with self._conn() as conn:
            conn.execute(
                "insert into jobs(job_id,status,created_at,updated_at,payload) values(?,?,?,?,?)",
                (job_id, "pending", now.isoformat(), now.isoformat(), json.dumps(payload, default=str)),
            )
        return self.get_job(job_id)  # type: ignore[return-value]

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._conn() as conn:
            row = conn.execute("select * from jobs where job_id=?", (job_id,)).fetchone()
            if not row:
                return None
            logs = self.logs_since(job_id, 0)
            result = json.loads(row["result"]) if row["result"] else None
            workflow_result = WorkflowResponse(**result) if result else None
            return JobRecord(
                job_id=row["job_id"],
                status=row["status"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                payload=json.loads(row["payload"]),
                result=workflow_result,
                error=row["error"],
                logs=logs,
            )

    def list_jobs(self) -> list[JobRecord]:
        with self._conn() as conn:
            rows = conn.execute("select job_id from jobs order by created_at desc").fetchall()
        return [self.get_job(r["job_id"]) for r in rows if self.get_job(r["job_id"]) is not None]  # type: ignore[list-item]

    def mark_running(self, job_id: str) -> None:
        self._update(job_id, status="running")

    def mark_success(self, job_id: str, result: WorkflowResponse) -> None:
        self._update(job_id, status="completed", result=json.dumps(result.model_dump()), error=None)

    def mark_failed(self, job_id: str, error: str) -> None:
        self._update(job_id, status="failed", error=error)

    def append_log(self, job_id: str, message: str, level: str = "info") -> None:
        with self._conn() as conn:
            seq_row = conn.execute("select coalesce(max(seq),0) as seq from job_logs where job_id=?", (job_id,)).fetchone()
            seq = int(seq_row["seq"]) + 1
            conn.execute(
                "insert into job_logs(job_id,seq,at,level,message) values(?,?,?,?,?)",
                (job_id, seq, datetime.now(timezone.utc).isoformat(), level, message),
            )
            conn.execute(
                "update jobs set updated_at=? where job_id=?",
                (datetime.now(timezone.utc).isoformat(), job_id),
            )

    def logs_since(self, job_id: str, last_seq: int) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "select seq,at,level,message from job_logs where job_id=? and seq>? order by seq asc",
                (job_id, last_seq),
            ).fetchall()
        return [dict(row) for row in rows]

    def _update(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        assignments = ", ".join([f"{k}=?" for k in fields])
        values = list(fields.values()) + [job_id]
        with self._conn() as conn:
            conn.execute(f"update jobs set {assignments} where job_id=?", values)
