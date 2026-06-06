from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..deps import get_db
from ..models import Image, Tag
from ..schemas import ImageDetail, ImageListResponse, ImageSummary, RatingUpdateRequest, TagUpdateRequest
from ..services.query_utils import apply_sort, build_image_filters

router = APIRouter(prefix="/api/images", tags=["images"])


def _split_loras(raw: str | None) -> list[str]:
    return [item.strip() for item in (raw or "").split(",") if item.strip()]


def _to_summary(model: Image) -> ImageSummary:
    return ImageSummary(
        id=model.id,
        gallery_id=model.gallery_id,
        path=model.path,
        name=model.name,
        ext=model.ext,
        width=model.width,
        height=model.height,
        size_bytes=model.size_bytes,
        mtime=model.mtime,
        rating=model.rating,
        tags=[tag.name for tag in model.tags],
        generator_source=model.generator_source or "Unknown",
        content_rating=model.content_rating or "unknown",
        checkpoint_name=model.checkpoint_name or "",
        lora_names=_split_loras(model.lora_names),
        positive_prompt=model.positive_prompt or "",
        positive_prompt_zh=model.positive_prompt_zh or "",
        steps=model.steps,
        cfg_scale=model.cfg_scale,
        sampler=model.sampler or "",
        schedule_type=model.schedule_type or "",
        clip_skip=model.clip_skip,
    )


@router.get("", response_model=ImageListResponse)
def list_images(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=60, ge=1, le=200),
    keyword: str | None = None,
    tag: str | None = None,
    generator: str | None = None,
    content_rating: str | None = None,
    checkpoint: str | None = None,
    lora: str | None = None,
    prompt_keyword: str | None = None,
    min_rating: int | None = Query(default=None, ge=0, le=5),
    max_rating: int | None = Query(default=None, ge=0, le=5),
    min_width: int | None = Query(default=None, ge=1),
    max_width: int | None = Query(default=None, ge=1),
    min_height: int | None = Query(default=None, ge=1),
    max_height: int | None = Query(default=None, ge=1),
    aspect_ratio: str | None = Query(default=None),
    sort_by: str = Query(default="newest"),
    gallery_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    filters = build_image_filters(
        keyword=keyword,
        tags=tag,
        generators=generator,
        content_ratings=content_rating,
        checkpoints=checkpoint,
        loras=lora,
        prompt_keyword=prompt_keyword,
        min_rating=min_rating,
        max_rating=max_rating,
        min_width=min_width,
        max_width=max_width,
        min_height=min_height,
        max_height=max_height,
        aspect_ratio=aspect_ratio,
        gallery_id=gallery_id,
    )

    base = select(Image).where(*filters).options(selectinload(Image.tags), selectinload(Image.gallery))
    ordered = apply_sort(base, sort_by)
    total = db.execute(select(func.count()).select_from(select(Image.id).where(*filters).subquery())).scalar_one()
    rows = db.execute(ordered.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return ImageListResponse(page=page, page_size=page_size, total=total, items=[_to_summary(row) for row in rows])


@router.get("/{image_id}", response_model=ImageDetail)
def get_image(image_id: int, db: Session = Depends(get_db)):
    model = db.execute(
        select(Image)
        .where(Image.id == image_id)
        .options(selectinload(Image.tags), selectinload(Image.gallery))
    ).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="Image not found")

    summary = _to_summary(model)
    return ImageDetail(
        **summary.model_dump(),
        gallery_name=model.gallery.name if model.gallery else None,
        negative_prompt=model.negative_prompt or "",
        vae_name=model.vae_name or "",
        seed=model.seed or "",
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.get("/{image_id}/preview")
def preview_image(image_id: int, db: Session = Depends(get_db)):
    model = db.execute(select(Image).where(Image.id == image_id)).scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="Image not found")

    path = Path(model.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file missing from disk")

    return FileResponse(path=path)


@router.post("/{image_id}/tags", response_model=ImageSummary)
def update_tags(image_id: int, payload: TagUpdateRequest, db: Session = Depends(get_db)):
    image = db.execute(select(Image).where(Image.id == image_id).options(selectinload(Image.tags))).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    clean_tags = [tag.strip().lower() for tag in payload.tags if tag.strip()]
    clean_tags = list(dict.fromkeys(clean_tags))
    tag_models = []
    for name in clean_tags:
        tag_model = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if tag_model is None:
            tag_model = Tag(name=name)
            db.add(tag_model)
            db.flush()
        tag_models.append(tag_model)

    image.tags = tag_models
    db.commit()
    db.refresh(image)
    image = db.execute(select(Image).where(Image.id == image_id).options(selectinload(Image.tags))).scalar_one()
    return _to_summary(image)


@router.post("/{image_id}/rating", response_model=ImageSummary)
def update_rating(image_id: int, payload: RatingUpdateRequest, db: Session = Depends(get_db)):
    image = db.execute(select(Image).where(Image.id == image_id).options(selectinload(Image.tags))).scalar_one_or_none()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    image.rating = payload.rating
    db.commit()
    db.refresh(image)
    image = db.execute(select(Image).where(Image.id == image_id).options(selectinload(Image.tags))).scalar_one()
    return _to_summary(image)
