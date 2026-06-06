import tempfile
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..deps import get_db
from ..models import Gallery, Image, Tag, image_tags
from ..schemas import BatchMoveRequest, ImageParseResponse, ManualSortActionRequest, ManualSortStartRequest, PromptLabGenerateRequest
from ..services.file_ops import move_image
from ..services.manual_sort import clear_session, get_current_payload, perform_action, start_session
from ..services.metadata import parse_image_file
from ..services.prompt_lab import generate_prompt, get_library_stats
from ..services.query_utils import apply_sort, build_image_filters
from ..services.similarity import compute_dhash, ensure_image_hash, find_similar_images

router = APIRouter(prefix="/api", tags=["tools"])


def _split_loras(raw: str | None) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def _to_summary(model: Image) -> dict:
    return {
        "id": model.id,
        "gallery_id": model.gallery_id,
        "path": model.path,
        "name": model.name,
        "ext": model.ext,
        "width": model.width,
        "height": model.height,
        "size_bytes": model.size_bytes,
        "mtime": model.mtime,
        "rating": model.rating,
        "tags": [tag.name for tag in model.tags],
        "generator_source": model.generator_source or "Unknown",
        "content_rating": model.content_rating or "unknown",
        "checkpoint_name": model.checkpoint_name or "",
        "lora_names": _split_loras(model.lora_names),
        "positive_prompt": model.positive_prompt or "",
        "positive_prompt_zh": model.positive_prompt_zh or "",
        "steps": model.steps,
        "cfg_scale": model.cfg_scale,
        "sampler": model.sampler or "",
        "schedule_type": model.schedule_type or "",
        "clip_skip": model.clip_skip,
    }


def _query_image_ids(db: Session, payload) -> list[int]:
    filters = build_image_filters(
        keyword=payload.keyword,
        tags=payload.tag,
        generators=payload.generator,
        content_ratings=payload.content_rating,
        checkpoints=payload.checkpoint,
        loras=payload.lora,
        prompt_keyword=payload.prompt_keyword,
        min_rating=payload.min_rating,
        max_rating=payload.max_rating,
        min_width=payload.min_width,
        max_width=payload.max_width,
        min_height=payload.min_height,
        max_height=payload.max_height,
        aspect_ratio=payload.aspect_ratio,
    )
    query = apply_sort(select(Image.id).where(*filters), getattr(payload, "sort_by", "newest"))
    return [row[0] for row in db.execute(query).all()]


@router.get("/galleries")
def list_galleries(db: Session = Depends(get_db)):
    galleries = db.execute(select(Gallery).order_by(Gallery.updated_at.desc(), Gallery.id.desc())).scalars().all()
    items = []
    for gallery in galleries:
        breakdown_rows = db.execute(
            select(Image.generator_source, func.count(Image.id))
            .where(Image.gallery_id == gallery.id)
            .group_by(Image.generator_source)
        ).all()
        items.append(
            {
                "id": gallery.id,
                "name": gallery.name,
                "path": gallery.path,
                "image_count": gallery.image_count,
                "last_scanned_at": gallery.last_scanned_at,
                "generator_breakdown": {str(name or "Unknown"): count for name, count in breakdown_rows},
            }
        )
    return {"items": items}


@router.get("/meta/tags")
def get_tag_library(limit: int = Query(default=200, ge=1, le=5000), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Tag.name, func.count(image_tags.c.image_id))
        .join(image_tags, image_tags.c.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(func.count(image_tags.c.image_id).desc(), Tag.name.asc())
        .limit(limit)
    ).all()
    return {"items": [{"value": name, "count": count} for name, count in rows]}


@router.get("/meta/generators")
def get_generator_library(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Image.generator_source, func.count(Image.id))
        .group_by(Image.generator_source)
        .order_by(func.count(Image.id).desc(), Image.generator_source.asc())
    ).all()
    return {"items": [{"value": str(name or "Unknown"), "count": count} for name, count in rows]}


@router.get("/meta/checkpoints")
def get_checkpoint_library(limit: int = Query(default=200, ge=1, le=5000), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Image.checkpoint_name, func.count(Image.id))
        .where(Image.checkpoint_name.is_not(None), Image.checkpoint_name != "")
        .group_by(Image.checkpoint_name)
        .order_by(func.count(Image.id).desc(), Image.checkpoint_name.asc())
        .limit(limit)
    ).all()
    return {"items": [{"value": name, "count": count} for name, count in rows]}


@router.get("/meta/loras")
def get_lora_library(limit: int = Query(default=200, ge=1, le=5000), db: Session = Depends(get_db)):
    counter: Counter[str] = Counter()
    for (raw,) in db.execute(select(Image.lora_names)).all():
        for name in [item.strip() for item in (raw or "").split(",") if item.strip()]:
            counter[name] += 1
    return {"items": [{"value": value, "count": count} for value, count in counter.most_common(limit)]}


@router.post("/reader/parse", response_model=ImageParseResponse)
async def parse_uploaded_image(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    suffix = Path(file.filename).suffix or ".png"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)

        parsed = parse_image_file(tmp_path)
        return ImageParseResponse(
            filename=file.filename,
            width=parsed["width"],
            height=parsed["height"],
            size_bytes=parsed["size_bytes"],
            generator_source=parsed["generator_source"],
            positive_prompt=parsed["positive_prompt"],
            positive_prompt_zh=parsed["positive_prompt_zh"],
            negative_prompt=parsed["negative_prompt"],
            checkpoint_name=parsed["checkpoint_name"],
            lora_names=parsed["lora_names"],
            vae_name=parsed["vae_name"],
            seed=parsed["seed"],
            steps=parsed["steps"],
            cfg_scale=parsed["cfg_scale"],
            sampler=parsed["sampler"],
            schedule_type=parsed["schedule_type"],
            clip_skip=parsed["clip_skip"],
            phash=parsed["phash"],
            metadata=parsed["metadata"],
        )
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@router.post("/batch-move")
def batch_move(payload: BatchMoveRequest, db: Session = Depends(get_db)):
    image_ids = payload.image_ids or _query_image_ids(db, payload)
    if not image_ids:
        raise HTTPException(status_code=400, detail="No images match batch move conditions")

    moved = 0
    errors: list[str] = []
    for image_id in image_ids:
        image = db.execute(select(Image).where(Image.id == image_id).options(selectinload(Image.tags))).scalar_one_or_none()
        if image is None:
            errors.append(f"Image {image_id} not found")
            continue
        try:
            move_image(db, image, payload.target_directory, payload.strategy)
            moved += 1
        except FileNotFoundError as exc:
            db.rollback()
            errors.append(str(exc))
    return {"requested": len(image_ids), "moved": moved, "errors": errors}


@router.get("/images/{image_id}/similar")
def get_similar_images(image_id: int, limit: int = Query(default=24, ge=1, le=200), db: Session = Depends(get_db)):
    image = db.execute(select(Image).where(Image.id == image_id).options(selectinload(Image.tags))).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    source_hash = ensure_image_hash(db, image)
    if not source_hash:
        raise HTTPException(status_code=400, detail="Could not compute image similarity hash")

    results = find_similar_images(db, source_hash=source_hash, exclude_image_id=image_id, limit=limit)
    return {
        "source": _to_summary(image),
        "items": [
            {
                "distance": distance,
                "score": max(0.0, round(1.0 - (distance / 64.0), 4)),
                "image": _to_summary(model),
            }
            for model, distance in results
        ],
    }


@router.post("/similar/upload")
async def get_similar_for_upload(
    file: UploadFile = File(...),
    limit: int = Query(default=24, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    suffix = Path(file.filename).suffix or ".png"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = Path(tmp.name)

        source_hash = compute_dhash(tmp_path)
        results = find_similar_images(db, source_hash=source_hash, limit=limit)
        return {
            "filename": file.filename,
            "source_hash": source_hash,
            "items": [
                {
                    "distance": distance,
                    "score": max(0.0, round(1.0 - (distance / 64.0), 4)),
                    "image": _to_summary(model),
                }
                for model, distance in results
            ],
        }
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@router.get("/prompt-lab/library")
def prompt_lab_library(limit: int = Query(default=200, ge=1, le=5000), db: Session = Depends(get_db)):
    return get_library_stats(db, limit=limit)


@router.post("/prompt-lab/generate")
def prompt_lab_generate(payload: PromptLabGenerateRequest, db: Session = Depends(get_db)):
    return generate_prompt(
        db,
        selected_tags=payload.selected_tags,
        quality_preset=payload.quality_preset,
        count_tag=payload.count_tag,
        include_negative=payload.include_negative,
        randomize=payload.randomize,
        seed=payload.seed,
    )


@router.post("/manual-sort/start")
def manual_sort_start(payload: ManualSortStartRequest, db: Session = Depends(get_db)):
    folders = {key.lower(): value for key, value in payload.folders.items() if value.strip()}
    if not folders:
        raise HTTPException(status_code=400, detail="At least one manual sort folder is required")

    for key, path in list(folders.items()):
        target = Path(path).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        folders[key] = str(target)

    image_ids = _query_image_ids(db, payload)
    if not image_ids:
        raise HTTPException(status_code=400, detail="No images match manual sort conditions")

    start_session(image_ids, folders)
    current = get_current_payload(db)
    if current.get("image") is not None:
        current["image"] = _to_summary(current["image"])
    return current


@router.get("/manual-sort/current")
def manual_sort_current(db: Session = Depends(get_db)):
    payload = get_current_payload(db)
    if payload.get("image") is not None:
        payload["image"] = _to_summary(payload["image"])
    return payload


@router.post("/manual-sort/action")
def manual_sort_action(payload: ManualSortActionRequest, db: Session = Depends(get_db)):
    result = perform_action(db, action=payload.action, folder_key=payload.folder_key.lower() if payload.folder_key else None)
    if result.get("error"):
        return result
    current = get_current_payload(db)
    if current.get("image") is not None:
        current["image"] = _to_summary(current["image"])
    current.update(result)
    return current


@router.delete("/manual-sort/session")
def manual_sort_clear():
    clear_session()
    return {"status": "cleared"}
