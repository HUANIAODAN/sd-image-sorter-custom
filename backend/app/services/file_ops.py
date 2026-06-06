import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Image


def _safe_name(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    idx = 1
    while True:
        candidate = parent / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
        idx += 1


def _resolve_target_dir(image: Image, target_directory: Path, strategy: str) -> Path:
    if strategy == "first_tag":
        tag_name = image.tags[0].name if image.tags else "untagged"
        return target_directory / tag_name
    if strategy == "rating":
        return target_directory / f"rating_{image.rating}"
    if strategy == "generator":
        return target_directory / (image.generator_source or "Unknown")
    if strategy == "content_rating":
        return target_directory / (image.content_rating or "unknown")
    return target_directory


def move_image(db: Session, image: Image, target_directory: str, strategy: str = "flat") -> tuple[str, str]:
    src = Path(image.path)
    if not src.exists():
        raise FileNotFoundError(f"Source image not found on disk: {src}")

    base_target = Path(target_directory).expanduser().resolve()
    final_dir = _resolve_target_dir(image, base_target, strategy)
    final_dir.mkdir(parents=True, exist_ok=True)

    desired = final_dir / src.name
    destination = _safe_name(desired)

    shutil.move(str(src), str(destination))
    old_path = image.path
    image.path = str(destination)
    image.name = destination.name
    image.ext = destination.suffix.lower()
    db.commit()

    return old_path, image.path
