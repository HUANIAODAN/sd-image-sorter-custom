from __future__ import annotations

import shutil
from pathlib import Path
from threading import Lock

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Image
from .file_ops import _safe_name

_LOCK = Lock()
_SESSION = {
    "active": False,
    "image_ids": [],
    "current_index": 0,
    "folders": {},
    "history": [],
}


def _session_counts() -> dict[str, int | bool]:
    history = _SESSION.get("history", [])
    return {
        "sorted_count": sum(1 for item in history if item.get("action") == "move"),
        "skipped_count": sum(1 for item in history if item.get("action") == "skip"),
        "undo_available": bool(history),
    }


def start_session(image_ids: list[int], folders: dict[str, str]) -> dict:
    with _LOCK:
        _SESSION["active"] = True
        _SESSION["image_ids"] = image_ids
        _SESSION["current_index"] = 0
        _SESSION["folders"] = folders
        _SESSION["history"] = []
        return {
            "status": "started",
            "total": len(image_ids),
            "folders": folders,
            **_session_counts(),
        }


def clear_session() -> None:
    with _LOCK:
        _SESSION["active"] = False
        _SESSION["image_ids"] = []
        _SESSION["current_index"] = 0
        _SESSION["folders"] = {}
        _SESSION["history"] = []


def get_state() -> dict:
    with _LOCK:
        return {
            "active": _SESSION["active"],
            "image_ids": list(_SESSION["image_ids"]),
            "current_index": _SESSION["current_index"],
            "folders": dict(_SESSION["folders"]),
            **_session_counts(),
        }


def get_current_payload(db: Session) -> dict:
    with _LOCK:
        image_ids = list(_SESSION["image_ids"])
        current_index = int(_SESSION["current_index"])
        folders = dict(_SESSION["folders"])
        counts = _session_counts()

    if not image_ids or current_index >= len(image_ids):
        return {"done": True, "folders": folders, **counts}

    image_id = image_ids[current_index]
    image = db.execute(
        select(Image).where(Image.id == image_id).options(selectinload(Image.tags), selectinload(Image.gallery))
    ).scalar_one_or_none()
    if image is None:
        with _LOCK:
            _SESSION["current_index"] += 1
        return get_current_payload(db)

    return {
        "done": False,
        "index": current_index,
        "total": len(image_ids),
        "remaining": len(image_ids) - current_index,
        "image_id": image.id,
        "folders": folders,
        "image_ids": image_ids,
        "image": image,
        **counts,
    }


def perform_action(db: Session, *, action: str, folder_key: str | None = None) -> dict:
    with _LOCK:
        image_ids = list(_SESSION["image_ids"])
        current_index = int(_SESSION["current_index"])
        folders = dict(_SESSION["folders"])
        history = _SESSION["history"]

    if action == "undo":
        with _LOCK:
            if not history:
                return {"status": "no_history", **_session_counts()}
            entry = history.pop()
            _SESSION["current_index"] = max(0, _SESSION["current_index"] - 1)

        if entry["action"] == "move":
            image = db.execute(select(Image).where(Image.id == entry["image_id"])).scalar_one_or_none()
            if image is not None:
                current_path = Path(image.path)
                original_path = Path(entry["original_path"])
                if current_path.exists():
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    destination = _safe_name(original_path) if original_path.exists() else original_path
                    shutil.move(str(current_path), str(destination))
                    image.path = str(destination)
                    image.name = destination.name
                    image.ext = destination.suffix.lower()
                    db.commit()
        return {"status": "undone", **_session_counts()}

    if current_index >= len(image_ids):
        return {"done": True, **_session_counts()}

    image_id = image_ids[current_index]
    image = db.execute(select(Image).where(Image.id == image_id).options(selectinload(Image.tags))).scalar_one_or_none()
    if image is None:
        with _LOCK:
            _SESSION["current_index"] += 1
        return get_current_payload(db)

    if action == "skip":
        with _LOCK:
            _SESSION["history"].append({"action": "skip", "image_id": image_id})
            _SESSION["current_index"] += 1
        return {"status": "skipped", **_session_counts()}

    if action == "move":
        if not folder_key or folder_key not in folders or not folders[folder_key]:
            return {"error": "Folder key is not configured", **_session_counts()}
        src = Path(image.path)
        if not src.exists():
            return {"error": "Image file missing from disk", **_session_counts()}

        target_dir = Path(folders[folder_key]).expanduser().resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        destination = _safe_name(target_dir / src.name)
        shutil.move(str(src), str(destination))
        original_path = image.path
        image.path = str(destination)
        image.name = destination.name
        image.ext = destination.suffix.lower()
        db.commit()

        with _LOCK:
            _SESSION["history"].append(
                {
                    "action": "move",
                    "image_id": image_id,
                    "folder_key": folder_key,
                    "original_path": original_path,
                    "new_path": image.path,
                }
            )
            _SESSION["current_index"] += 1
        return {"status": "moved", "folder_key": folder_key, **_session_counts()}

    return {"error": "Unsupported action", **_session_counts()}
