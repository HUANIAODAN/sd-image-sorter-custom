from pathlib import Path
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Gallery, Image
from .metadata import extract_metadata

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}


def _iter_image_files(directory: Path, recursive: bool):
    iterator = directory.rglob("*") if recursive else directory.glob("*")
    for p in iterator:
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES:
            yield p


def _get_or_create_gallery(db: Session, directory: Path) -> Gallery:
    abs_path = str(directory)
    gallery = db.execute(select(Gallery).where(Gallery.path == abs_path)).scalar_one_or_none()
    if gallery is None:
        gallery = Gallery(name=directory.name or abs_path, path=abs_path, last_scanned_at=datetime.utcnow())
        db.add(gallery)
        db.flush()
        return gallery

    gallery.name = directory.name or abs_path
    gallery.last_scanned_at = datetime.utcnow()
    db.flush()
    return gallery


def _refresh_gallery_stats(db: Session, gallery: Gallery) -> None:
    gallery.image_count = db.execute(select(func.count(Image.id)).where(Image.gallery_id == gallery.id)).scalar_one()
    gallery.last_scanned_at = datetime.utcnow()
    db.flush()


def scan_directory(db: Session, directory: str, recursive: bool = True, max_files: int | None = None) -> dict:
    base = Path(directory).expanduser().resolve()
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"Directory does not exist: {base}")

    gallery = _get_or_create_gallery(db, base)
    scanned = added = updated = skipped = 0

    for image_path in _iter_image_files(base, recursive):
        if max_files is not None and scanned >= max_files:
            break

        scanned += 1
        abs_path = str(image_path)
        metadata = extract_metadata(image_path)

        record = db.execute(select(Image).where(Image.path == abs_path)).scalar_one_or_none()
        if record is None:
            db.add(
                Image(
                    gallery_id=gallery.id,
                    path=abs_path,
                    name=metadata["name"],
                    ext=metadata["ext"],
                    width=metadata["width"],
                    height=metadata["height"],
                    size_bytes=metadata["size_bytes"],
                    mtime=metadata["mtime"],
                    generator_source=metadata["generator_source"],
                    positive_prompt=metadata["positive_prompt"],
                    negative_prompt=metadata["negative_prompt"],
                    positive_prompt_zh=metadata["positive_prompt_zh"],
                    checkpoint_name=metadata["checkpoint_name"],
                    lora_names=metadata["lora_names"],
                    vae_name=metadata["vae_name"],
                    seed=metadata["seed"],
                    steps=metadata["steps"],
                    cfg_scale=metadata["cfg_scale"],
                    sampler=metadata["sampler"],
                    schedule_type=metadata["schedule_type"],
                    clip_skip=metadata["clip_skip"],
                    content_rating=metadata["content_rating"],
                    phash=metadata["phash"],
                )
            )
            added += 1
            continue

        changed = False
        if record.gallery_id != gallery.id:
            record.gallery_id = gallery.id
            changed = True
        for key in (
            "name",
            "ext",
            "width",
            "height",
            "size_bytes",
            "mtime",
            "generator_source",
            "positive_prompt",
            "negative_prompt",
            "positive_prompt_zh",
            "checkpoint_name",
            "lora_names",
            "vae_name",
            "seed",
            "steps",
            "cfg_scale",
            "sampler",
            "schedule_type",
            "clip_skip",
            "content_rating",
            "phash",
        ):
            value = metadata[key]
            if getattr(record, key) != value:
                setattr(record, key, value)
                changed = True

        if changed:
            updated += 1
        else:
            skipped += 1

    _refresh_gallery_stats(db, gallery)
    db.commit()
    return {
        "scanned": scanned,
        "added": added,
        "updated": updated,
        "skipped": skipped,
        "gallery_id": gallery.id,
        "gallery_name": gallery.name,
    }
