"""
Aesthetic Score Service
使用预训练模型对图片进行美学评分
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# 全局模型实例
_model = None
_preprocess = None


def _get_model_path() -> Path:
    """获取美学评分模型路径"""
    return Path(__file__).resolve().parents[3] / "models" / "aesthetic"


def _ensure_model():
    """确保模型已加载"""
    global _model, _preprocess

    if _model is not None:
        return "loaded"

    model_dir = _get_model_path()
    model_file = model_dir / "aesthetic_predictor.pth"

    if not model_file.exists():
        logger.warning(f"Aesthetic model not found at {model_file}")
        return "missing"

    try:
        import torch
        import torch.nn as nn
        from torchvision import transforms

        # 简单的美学评分模型架构
        class AestheticPredictor(nn.Module):
            def __init__(self):
                super().__init__()
                self.features = nn.Sequential(
                    nn.Conv2d(3, 64, 3, padding=1),
                    nn.ReLU(),
                    nn.MaxPool2d(2),
                    nn.Conv2d(64, 128, 3, padding=1),
                    nn.ReLU(),
                    nn.MaxPool2d(2),
                    nn.AdaptiveAvgPool2d((1, 1)),
                    nn.Flatten(),
                )
                self.classifier = nn.Sequential(
                    nn.Linear(128, 64),
                    nn.ReLU(),
                    nn.Dropout(0.5),
                    nn.Linear(64, 1),
                )

            def forward(self, x):
                x = self.features(x)
                x = self.classifier(x)
                return x.squeeze()

        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = AestheticPredictor().to(device)

        if model_file.exists():
            try:
                _model.load_state_dict(torch.load(model_file, map_location=device))
                _model.eval()
                logger.info(f"Loaded aesthetic model from {model_file}")
            except Exception as e:
                logger.warning(f"Failed to load model weights: {e}")

        from torchvision import transforms
        _preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        return "loaded"

    except ImportError as e:
        logger.error(f"Failed to import required packages: {e}")
        return "error"
    except Exception as e:
        logger.error(f"Failed to load aesthetic model: {e}")
        return "error"


def get_runtime_info() -> dict:
    """获取美学评分运行时信息"""
    status = _ensure_model()
    model_dir = _get_model_path()

    return {
        "status": status,
        "model_path": str(model_dir),
        "model_exists": (model_dir / "aesthetic_predictor.pth").exists(),
    }


def score_image(image_path: Path) -> Optional[float]:
    """对单张图片进行美学评分，返回 0-10 分"""
    status = _ensure_model()

    if status != "loaded":
        logger.warning(f"Aesthetic model not available: {status}")
        return None

    try:
        import torch

        img = Image.open(image_path).convert("RGB")
        input_tensor = _preprocess(img).unsqueeze(0)
        device = next(_model.parameters()).device
        input_tensor = input_tensor.to(device)

        with torch.no_grad():
            score = _model(input_tensor).item()

        if score < 0:
            score = 0
        elif score > 10:
            score = 10
        elif score <= 1:
            score = score * 10

        return round(score, 2)

    except Exception as e:
        logger.error(f"Failed to score image {image_path}: {e}")
        return None


def estimate_aesthetic_fallback(image_path: Path) -> float:
    """回退评分方法，基于简单的图像特征"""
    try:
        import cv2

        img = cv2.imread(str(image_path))
        if img is None:
            return 5.0

        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        img_lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)

        brightness = np.mean(img_lab[:, :, 0]) / 255.0
        contrast = np.std(img_lab[:, :, 0]) / 255.0
        saturation = np.mean(img_hsv[:, :, 1]) / 255.0

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness = min(laplacian_var / 1000.0, 1.0)

        score = (
            brightness * 1.5 +
            contrast * 2.0 +
            saturation * 1.5 +
            sharpness * 3.0
        )

        score = min(max(score, 0), 10)
        return round(score, 2)

    except Exception as e:
        logger.error(f"Failed to estimate aesthetic for {image_path}: {e}")
        return 5.0
