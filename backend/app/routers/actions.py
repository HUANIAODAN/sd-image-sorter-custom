import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import SessionLocal
from ..deps import get_db
from ..models import Image
from ..schemas import (
    AutoTagBatchStartRequest,
    AutoTagBatchStartResponse,
    AutoTagBatchStatusResponse,
    AutoTagRequest,
    AutoTagResponse,
    AutoTagRuntimeStatusResponse,
    MoveImageRequest,
    MoveImageResponse,
    ScanRequest,
    ScanResponse,
)
from ..services.autotag import apply_tags, generate_tags_for_image
from ..services.autotag_jobs import (
    create_job,
    get_job,
    mark_done,
    mark_failed,
    mark_progress,
    mark_running,
)
from ..services.file_ops import move_image
from ..services.scanner import scan_directory
from ..services.wd14 import get_wd14_status

router = APIRouter(prefix="/api", tags=["actions"])


@router.post("/scan", response_model=ScanResponse)
def scan(payload: ScanRequest, db: Session = Depends(get_db)):
    try:
        result = scan_directory(
            db=db,
            directory=payload.directory,
            recursive=payload.recursive,
            max_files=payload.max_files,
        )
        return ScanResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/move", response_model=MoveImageResponse)
def move(payload: MoveImageRequest, db: Session = Depends(get_db)):
    image = db.execute(select(Image).where(Image.id == payload.image_id).options(selectinload(Image.tags))).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        old_path, new_path = move_image(db, image, payload.target_directory, payload.strategy)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MoveImageResponse(image_id=image.id, old_path=old_path, new_path=new_path)


@router.post("/auto-tag", response_model=AutoTagResponse)
def auto_tag(payload: AutoTagRequest, db: Session = Depends(get_db)):
    image = db.execute(select(Image).where(Image.id == payload.image_id)).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    tags, source, content_rating = generate_tags_for_image(image.path)
    tags = apply_tags(db, image, tags, content_rating)
    source = "wd14" if source == "wd14" else "filename_fallback"
    return AutoTagResponse(image_id=image.id, tags=tags, source=source, content_rating=content_rating)


@router.get("/auto-tag/runtime", response_model=AutoTagRuntimeStatusResponse)
def auto_tag_runtime_status():
    available, detail = get_wd14_status()
    mode = "wd14" if available else "filename_fallback"
    return AutoTagRuntimeStatusResponse(model_available=available, mode=mode, detail=detail)


def _run_batch_auto_tag_job(
    job_id: str,
    image_ids: list[int],
    general_threshold: float,
    character_threshold: float,
) -> None:
    mark_running(job_id)

    processed = success = failed = skipped = 0
    db = SessionLocal()
    try:
        for image_id in image_ids:
            image = db.execute(select(Image).where(Image.id == image_id).options(selectinload(Image.tags))).scalar_one_or_none()
            if image is None:
                processed += 1
                skipped += 1
                mark_progress(
                    job_id,
                    processed=processed,
                    success=success,
                    failed=failed,
                    skipped=skipped,
                    current_image_id=image_id,
                )
                continue

            try:
                tags, _source, content_rating = generate_tags_for_image(
                    image.path,
                    general_threshold=general_threshold,
                    character_threshold=character_threshold,
                )
                if not tags:
                    skipped += 1
                else:
                    apply_tags(db, image, tags, content_rating)
                    success += 1
            except Exception:
                db.rollback()
                failed += 1

            processed += 1
            mark_progress(
                job_id,
                processed=processed,
                success=success,
                failed=failed,
                skipped=skipped,
                current_image_id=image_id,
            )

        mark_done(job_id)
    except Exception as exc:
        mark_failed(job_id, str(exc))
    finally:
        db.close()


@router.post("/auto-tag/batch", response_model=AutoTagBatchStartResponse)
def auto_tag_batch_start(
    payload: AutoTagBatchStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    query = select(Image.id).order_by(Image.id.asc())
    if payload.image_ids:
        query = query.where(Image.id.in_(payload.image_ids))
    if payload.only_untagged:
        query = query.where(~Image.tags.any())

    image_ids = [row[0] for row in db.execute(query).all()]
    if not image_ids:
        raise HTTPException(status_code=400, detail="No images match batch auto-tag conditions")

    job_id = str(uuid.uuid4())
    has_wd14, wd14_message = get_wd14_status()
    mode = "wd14" if has_wd14 else "filename_fallback"

    create_job(job_id=job_id, total=len(image_ids), mode=mode)
    background_tasks.add_task(
        _run_batch_auto_tag_job,
        job_id,
        image_ids,
        payload.general_threshold,
        payload.character_threshold,
    )
    note = None if has_wd14 else f"WD14 not available, using filename fallback. reason: {wd14_message}"
    return AutoTagBatchStartResponse(job_id=job_id, total=len(image_ids), mode=mode, note=note)


@router.get("/auto-tag/batch/{job_id}", response_model=AutoTagBatchStatusResponse)
def auto_tag_batch_status(job_id: str):
    state = get_job(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Batch job not found")
    return AutoTagBatchStatusResponse(**state.to_dict())
