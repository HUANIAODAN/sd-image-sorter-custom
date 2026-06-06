from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from threading import Lock


@dataclass
class AutoTagJobState:
    job_id: str
    mode: str
    status: str
    total: int
    processed: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    current_image_id: int | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["progress"] = 0.0 if self.total <= 0 else round((self.processed / self.total) * 100, 2)
        return data


_JOBS: dict[str, AutoTagJobState] = {}
_LOCK = Lock()


def create_job(job_id: str, total: int, mode: str) -> AutoTagJobState:
    state = AutoTagJobState(job_id=job_id, total=total, mode=mode, status="pending")
    with _LOCK:
        _JOBS[job_id] = state
    return state


def get_job(job_id: str) -> AutoTagJobState | None:
    with _LOCK:
        return _JOBS.get(job_id)


def mark_running(job_id: str) -> None:
    with _LOCK:
        state = _JOBS.get(job_id)
        if state is None:
            return
        state.status = "running"
        state.started_at = datetime.utcnow()


def mark_progress(
    job_id: str,
    *,
    processed: int,
    success: int,
    failed: int,
    skipped: int,
    current_image_id: int | None,
) -> None:
    with _LOCK:
        state = _JOBS.get(job_id)
        if state is None:
            return
        state.processed = processed
        state.success = success
        state.failed = failed
        state.skipped = skipped
        state.current_image_id = current_image_id


def mark_done(job_id: str) -> None:
    with _LOCK:
        state = _JOBS.get(job_id)
        if state is None:
            return
        state.status = "completed"
        state.current_image_id = None
        state.finished_at = datetime.utcnow()


def mark_failed(job_id: str, error: str) -> None:
    with _LOCK:
        state = _JOBS.get(job_id)
        if state is None:
            return
        state.status = "failed"
        state.current_image_id = None
        state.error = error
        state.finished_at = datetime.utcnow()
