"""
CLIP Similarity Router
CLIP 相似度搜索相关 API 路由
"""
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..deps import get_db
from ..models import Image
from ..services.clip_similarity import (
    get_runtime_info,
    compute_clip_embedding,
    find_similar_by_embedding,
)
import numpy as np

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/clip", tags=["clip"])


class ComputeEmbeddingRequest(BaseModel):
    image_id: int


@router.get("/runtime")
def clip_runtime():
    """获取 CLIP 运行时信息"""
    return get_runtime_info()


@router.post("/compute-embedding")
def compute_embedding_single(payload: ComputeEmbeddingRequest, db: Session = Depends(get_db)):
    """计算单张图片的 CLIP embedding"""
    image = db.execute(select(Image).where(Image.id == payload.image_id)).scalar_one_or_none()

    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    image_path = Path(image.path)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    embedding = compute_clip_embedding(image_path)

    if embedding is None:
        raise HTTPException(status_code=500, detail="Failed to compute embedding")

    image.clip_embedding = embedding.astype(np.float32).tobytes()
    db.commit()

    return {"image_id": image.id, "status": "success"}


@router.get("/images/{image_id}/similar-clip")
def get_similar_clip(
    image_id: int,
    limit: int = Query(default=24, ge=1, le=200),
    threshold: float = Query(default=0.7, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """使用 CLIP 查找相似图片"""
    image = db.execute(
        select(Image).where(Image.id == image_id).options(selectinload(Image.tags))
    ).scalar_one_or_none()

    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    if image.clip_embedding is None:
        image_path = Path(image.path)
        embedding = compute_clip_embedding(image_path)
        if embedding is None:
            raise HTTPException(status_code=500, detail="Failed to compute embedding")
        image.clip_embedding = embedding.astype(np.float32).tobytes()
        db.commit()
    else:
        embedding = np.frombuffer(image.clip_embedding, dtype=np.float32)

    similar_ids = find_similar_by_embedding(db, embedding, limit, threshold, image_id)

    results = []
    for img_id, similarity in similar_ids:
        similar_img = db.execute(
            select(Image).where(Image.id == img_id).options(selectinload(Image.tags))
        ).scalar_one_or_none()

        if similar_img:
            results.append({"similarity": round(similarity, 4), "image": {"id": similar_img.id, "name": similar_img.name}})

    return {"items": results}
