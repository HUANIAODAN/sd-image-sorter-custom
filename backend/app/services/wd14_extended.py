"""
Extended WD14 Tagger - Multi-Model Support
支持多个 WD14 扩展模型
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .wd14 import WD14Tagger, WD14PredictResult

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[3]
MODELS_DIR = ROOT_DIR / "models" / "wd14"

# 模型配置
AVAILABLE_MODELS = {
    "wd14-v2": {
        "name": "WD14 v2 (Original)",
        "model_file": "model.onnx",
        "tags_file": "selected_tags.csv",
        "description": "Original WD14 v2 tagger",
    },
    "cl-tagger": {
        "name": "CL Tagger v1.02",
        "model_file": "cl_tagger_model.onnx",
        "tags_file": "cl_tagger_tags.csv",
        "description": "Improved character recognition",
        "huggingface_repo": "Nonene/cl_tagger",
    },
    "pixai-tagger": {
        "name": "PixAI Tagger v0.9",
        "model_file": "pixai_tagger_model.onnx",
        "tags_file": "pixai_tagger_tags.csv",
        "description": "Optimized for anime",
        "huggingface_repo": "pixai-labs/pixai-tagger-v0.9",
    },
    "wd-eva02-large": {
        "name": "WD EVA02 Large v3",
        "model_file": "wd_eva02_large_model.onnx",
        "tags_file": "wd_eva02_large_tags.csv",
        "description": "Most accurate tagger",
        "huggingface_repo": "SmilingWolf/wd-eva02-large-tagger-v3",
    },
}


class MultiModelWD14Manager:
    """管理多个 WD14 模型的类"""

    def __init__(self):
        self._taggers: dict[str, WD14Tagger] = {}
        self._current_model = "wd14-v2"

    def get_available_models(self) -> list[dict]:
        """获取所有可用模型的信息"""
        models_info = []
        for model_id, config in AVAILABLE_MODELS.items():
            model_path = MODELS_DIR / config["model_file"]
            tags_path = MODELS_DIR / config["tags_file"]
            is_available = model_path.exists() and tags_path.exists()

            models_info.append({
                "id": model_id,
                "name": config["name"],
                "description": config["description"],
                "available": is_available,
                "is_current": model_id == self._current_model,
            })

        return models_info

    def get_tagger(self, model_id: Optional[str] = None) -> WD14Tagger:
        """获取指定模型的 tagger"""
        if model_id is None:
            model_id = self._current_model

        if model_id not in AVAILABLE_MODELS:
            raise ValueError(f"Unknown model: {model_id}")

        if model_id in self._taggers:
            return self._taggers[model_id]

        config = AVAILABLE_MODELS[model_id]
        model_path = MODELS_DIR / config["model_file"]
        tags_path = MODELS_DIR / config["tags_file"]

        tagger = WD14Tagger(model_path=model_path, tags_path=tags_path)
        self._taggers[model_id] = tagger

        return tagger

    def set_current_model(self, model_id: str) -> None:
        """设置当前使用的模型"""
        if model_id not in AVAILABLE_MODELS:
            raise ValueError(f"Unknown model: {model_id}")
        self._current_model = model_id
        logger.info(f"Current WD14 model set to: {model_id}")

    def predict(
        self,
        image_path: str,
        model_id: Optional[str] = None,
        general_threshold: float = 0.35,
        character_threshold: float = 0.85,
        rating_threshold: float = 0.5,
        max_tags: int = 60,
    ) -> tuple[WD14PredictResult, str]:
        """使用指定模型进行预测"""
        if model_id is None:
            model_id = self._current_model

        tagger = self.get_tagger(model_id)
        result = tagger.predict(
            image_path=image_path,
            general_threshold=general_threshold,
            character_threshold=character_threshold,
            rating_threshold=rating_threshold,
            max_tags=max_tags,
        )

        return result, model_id


# 全局实例
_multi_model_manager = MultiModelWD14Manager()


def get_multi_model_manager() -> MultiModelWD14Manager:
    return _multi_model_manager


def get_available_wd14_models() -> list[dict]:
    return _multi_model_manager.get_available_models()
