"""
Aesthetic Score Router
美学评分相关 API 路由
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Image
from ..services.aesthetic_scorer import (
    get_runtime_info,
    score_image,
    estimate_aesthetic_fallback,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/aesthetic", tags=["aesthetic"])


class ScoreImageRequest(BaseModel):
    image_id: int
    use_fallback: bool = False


class BatchScoreRequest(BaseModel):
    image_ids: list[int] | None = None
    only_unscored: bool = True
    use_fallback: bool = False


@router.get("/runtime")
def aesthetic_runtime():
    """获取美学评分运行时信息"""
    return get_runtime_info()


@router.post("/score")
def score_single_image(payload: ScoreImageRequest, db: Session = Depends(get_db)):
    """为单张图片评分"""
    image = db.execute(select(Image).where(Image.id == payload.image_id)).scalar_one_or_none()

    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    image_path = Path(image.path)

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk")

    try:
        if payload.use_fallback:
            score = estimate_aesthetic_fallback(image_path)
        else:
            score = score_image(image_path)
            if score is None:
                # 模型不可用，回退
                score = estimate_aesthetic_fallback(image_path)

        # 更新数据库
        image.aesthetic_score = score
        db.commit()

        return {
            "image_id": image.id,
            "aesthetic_score": score,
            "method": "fallback" if payload.use_fallback else "model",
        }

    except Exception as e:
        logger.error(f"Failed to score image {image.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _batch_score_task(db: Session, image_ids: list[int], use_fallback: bool):
    """后台任务：批量评分"""
    success_count = 0
    failed_count = 0

    for image_id in image_ids:
        try:
            image = db.execute(select(Image).where(Image.id == image_id)).scalar_one_or_none()
            if image is None:
                failed_count += 1
                continue

            image_path = Path(image.path)
            if not image_path.exists():
                failed_count += 1
                continue

            if use_fallback:
                score = estimate_aesthetic_fallback(image_path)
            else:
                score = score_image(image_path)
                if score is None:
                    score = estimate_aesthetic_fallback(image_path)

            image.aesthetic_score = score
            db.commit()
            success_count += 1

        except Exception as e:
            logger.error(f"Failed to score image {image_id}: {e}")
            failed_count += 1
            db.rollback()

    logger.info(f"Batch scoring completed: {success_count} success, {failed_count} failed")


@router.post("/batch")
def batch_score_images(
    payload: BatchScoreRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """批量评分图片（后台任务）"""
    if payload.image_ids:
        image_ids = payload.image_ids
    else:
        # 获取所有未评分的图片
        query = select(Image.id)
        if payload.only_unscored:
            query = query.where(Image.aesthetic_score.is_(None))

        image_ids = [row[0] for row in db.execute(query).all()]

    if not image_ids:
        raise HTTPException(status_code=400, detail="No images to score")

    # 添加后台任务
    background_tasks.add_task(_batch_score_task, db, image_ids, payload.use_fallback)

    return {
        "status": "started",
        "total": len(image_ids),
        "message": f"Batch scoring {len(image_ids)} images in background",
    }


@router.get("/stats")
def aesthetic_stats(db: Session = Depends(get_db)):
    """获取美学评分统计信息"""
    from sqlalchemy import func

    stats = db.execute(
        select(
            func.count(Image.id).label("total"),
            func.count(Image.aesthetic_score).label("scored"),
            func.avg(Image.aesthetic_score).label("avg_score"),
            func.min(Image.aesthetic_score).label("min_score"),
            func.max(Image.aesthetic_score).label("max_score"),
        )
    ).one()

    return {
        "total_images": stats.total,
        "scored_images": stats.scored,
        "unscored_images": stats.total - stats.scored,
        "average_score": round(float(stats.avg_score), 2) if stats.avg_score else None,
        "min_score": float(stats.min_score) if stats.min_score else None,
        "max_score": float(stats.max_score) if stats.max_score else None,
    }
