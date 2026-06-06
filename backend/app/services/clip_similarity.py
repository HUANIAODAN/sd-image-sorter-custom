"""
CLIP-based Similarity Service
使用 CLIP embedding 进行语义相似度搜索
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# 全局模型实例
_model = None
_processor = None


def _get_model_path() -> Path:
    """获取 CLIP 模型路径"""
    return Path(__file__).resolve().parents[3] / "models" / "clip"


def _ensure_model():
    """确保 CLIP 模型已加载"""
    global _model, _processor

    if _model is not None:
        return "loaded"

    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor

        model_dir = _get_model_path()

        # 尝试从本地加载，否则从 HuggingFace 下载
        if model_dir.exists() and (model_dir / "config.json").exists():
            logger.info(f"Loading CLIP model from {model_dir}")
            _model = CLIPModel.from_pretrained(model_dir)
            _processor = CLIPProcessor.from_pretrained(model_dir)
        else:
            logger.info("Downloading CLIP model from HuggingFace...")
            _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

            # 保存到本地
            model_dir.mkdir(parents=True, exist_ok=True)
            _model.save_pretrained(model_dir)
            _processor.save_pretrained(model_dir)

        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = _model.to(device)
        _model.eval()

        logger.info(f"CLIP model loaded on {device}")
        return "loaded"

    except ImportError as e:
        logger.error(f"Failed to import required packages: {e}")
        return "error"
    except Exception as e:
        logger.error(f"Failed to load CLIP model: {e}")
        return "error"


def get_runtime_info() -> dict:
    """获取 CLIP 运行时信息"""
    status = _ensure_model()
    model_dir = _get_model_path()

    return {
        "status": status,
        "model_path": str(model_dir),
        "model_exists": model_dir.exists() and (model_dir / "config.json").exists(),
        "device": "cuda" if _model and next(_model.parameters()).is_cuda else "cpu" if _model else "n/a",
    }


def compute_clip_embedding(image_path: Path) -> Optional[np.ndarray]:
    """
    计算图片的 CLIP embedding

    Args:
        image_path: 图片路径

    Returns:
        CLIP embedding (512维向量) 或 None
    """
    status = _ensure_model()

    if status != "loaded":
        logger.warning(f"CLIP model not available: {status}")
        return None

    try:
        import torch

        img = Image.open(image_path).convert("RGB")
        inputs = _processor(images=img, return_tensors="pt")

        device = next(_model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            image_features = _model.get_image_features(**inputs)
            # 归一化
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        embedding = image_features.cpu().numpy().flatten()
        return embedding

    except Exception as e:
        logger.error(f"Failed to compute CLIP embedding for {image_path}: {e}")
        return None


def compute_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    计算两个 CLIP embedding 的余弦相似度

    Args:
        embedding1: 第一个 embedding
        embedding2: 第二个 embedding

    Returns:
        相似度分数 (0-1)
    """
    try:
        # 余弦相似度
        similarity = np.dot(embedding1, embedding2)
        return float(similarity)

    except Exception as e:
        logger.error(f"Failed to compute similarity: {e}")
        return 0.0


def find_similar_by_embedding(
    db_session,
    source_embedding: np.ndarray,
    limit: int = 24,
    threshold: float = 0.5,
    exclude_image_id: Optional[int] = None,
) -> list[tuple[int, float]]:
    """
    根据 CLIP embedding 查找相似图片

    Args:
        db_session: 数据库会话
        source_embedding: 源图片的 embedding
        limit: 返回结果数量
        threshold: 相似度阈值
        exclude_image_id: 排除的图片 ID

    Returns:
        [(image_id, similarity_score), ...] 列表
    """
    from sqlalchemy import select
    from ..models import Image

    try:
        # 获取所有有 embedding 的图片
        query = select(Image.id, Image.clip_embedding).where(Image.clip_embedding.is_not(None))
        if exclude_image_id:
            query = query.where(Image.id != exclude_image_id)

        results = db_session.execute(query).all()

        similarities = []
        for image_id, embedding_blob in results:
            if embedding_blob is None:
                continue

            # 反序列化 embedding
            embedding = np.frombuffer(embedding_blob, dtype=np.float32)

            # 计算相似度
            similarity = compute_similarity(source_embedding, embedding)

            if similarity >= threshold:
                similarities.append((image_id, similarity))

        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:limit]

    except Exception as e:
        logger.error(f"Failed to find similar images: {e}")
        return []


def batch_compute_embeddings(image_paths: list[Path], batch_size: int = 16) -> dict[str, Optional[np.ndarray]]:
    """
    批量计算 CLIP embeddings

    Args:
        image_paths: 图片路径列表
        batch_size: 批处理大小

    Returns:
        {路径: embedding} 字典
    """
    status = _ensure_model()

    if status != "loaded":
        logger.warning(f"CLIP model not available: {status}")
        return {str(path): None for path in image_paths}

    results = {}

    try:
        import torch

        device = next(_model.parameters()).device

        # 分批处理
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            images = []
            valid_paths = []

            # 加载批次图片
            for path in batch_paths:
                try:
                    img = Image.open(path).convert("RGB")
                    images.append(img)
                    valid_paths.append(path)
                except Exception as e:
                    logger.warning(f"Failed to load image {path}: {e}")
                    results[str(path)] = None

            if not images:
                continue

            # 批量处理
            inputs = _processor(images=images, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}

            with torch.no_grad():
                image_features = _model.get_image_features(**inputs)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            embeddings = image_features.cpu().numpy()

            # 保存结果
            for path, embedding in zip(valid_paths, embeddings):
                results[str(path)] = embedding

        return results

    except Exception as e:
        logger.error(f"Failed to batch compute embeddings: {e}")
        return {str(path): None for path in image_paths}
