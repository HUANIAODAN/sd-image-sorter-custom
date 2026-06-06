"""
WD14 Extended Models Router
多模型管理 API 路由
"""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Image
from ..services.wd14_extended import (
    get_multi_model_manager,
    get_available_wd14_models,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/wd14", tags=["wd14-extended"])


class SetModelRequest(BaseModel):
    model_id: str


class PredictRequest(BaseModel):
    image_id: int
    model_id: str | None = None
    general_threshold: float = 0.35
    character_threshold: float = 0.85


@router.get("/models")
def list_wd14_models():
    """获取所有可用的 WD14 模型列表"""
    models = get_available_wd14_models()
    return {"models": models}


@router.get("/current-model")
def get_current_model():
    """获取当前使用的模型"""
    manager = get_multi_model_manager()
    current = manager._current_model

    models = get_available_wd14_models()
    current_info = next((m for m in models if m["id"] == current), None)

    return {
        "current_model_id": current,
        "current_model_info": current_info
    }


@router.post("/set-model")
def set_current_model(payload: SetModelRequest):
    """设置当前使用的模型"""
    manager = get_multi_model_manager()

    try:
        manager.set_current_model(payload.model_id)
        return {
            "success": True,
            "model_id": payload.model_id,
            "message": f"Successfully switched to {payload.model_id}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/predict")
def predict_with_model(payload: PredictRequest, db: Session = Depends(get_db)):
    """使用指定模型对图片进行标签预测"""
    from sqlalchemy import select

    image = db.execute(select(Image).where(Image.id == payload.image_id)).scalar_one_or_none()

    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    image_path = Path(image.path)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    manager = get_multi_model_manager()

    try:
        result, used_model = manager.predict(
            image_path=str(image_path),
            model_id=payload.model_id,
            general_threshold=payload.general_threshold,
            character_threshold=payload.character_threshold,
        )

        return {
            "image_id": image.id,
            "model_used": used_model,
            "tags": result.tags,
            "ratings": result.ratings,
            "tag_count": len(result.tags)
        }

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-status/{model_id}")
def get_model_status(model_id: str):
    """获取指定模型的状态"""
    manager = get_multi_model_manager()

    try:
        available, message = manager.get_model_status(model_id)
        return {
            "model_id": model_id,
            "available": available,
            "message": message
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
