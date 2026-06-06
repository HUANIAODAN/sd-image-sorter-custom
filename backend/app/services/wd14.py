from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from PIL import Image

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional dependency at runtime
    np = None

try:
    import onnxruntime as ort
except ImportError:  # pragma: no cover - optional dependency at runtime
    ort = None

ROOT_DIR = Path(__file__).resolve().parents[3]
WD14_DIR = ROOT_DIR / "models" / "wd14"
DEFAULT_MODEL_PATH = WD14_DIR / "model.onnx"
DEFAULT_TAGS_PATH = WD14_DIR / "selected_tags.csv"


@dataclass(frozen=True)
class WD14TagMeta:
    name: str
    category: int


@dataclass(frozen=True)
class WD14PredictResult:
    tags: list[str]
    ratings: list[str]


class WD14RuntimeError(RuntimeError):
    pass


def _normalize_tag_name(name: str) -> str:
    return name.strip().replace("_", " ")


def _read_tag_metadata(csv_path: Path) -> list[WD14TagMeta]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise WD14RuntimeError(f"No rows found in tags file: {csv_path}")

    tag_metas: list[WD14TagMeta] = []
    for row in rows:
        values = list(row.values())
        raw_name = row.get("name") or row.get("tag") or (values[1] if len(values) > 1 else "")
        raw_category = row.get("category") or (values[2] if len(values) > 2 else "0")
        if not raw_name:
            continue
        try:
            category = int(raw_category)
        except ValueError:
            category = 0
        tag_metas.append(WD14TagMeta(name=_normalize_tag_name(raw_name), category=category))

    if not tag_metas:
        raise WD14RuntimeError(f"Could not parse tag names from: {csv_path}")
    return tag_metas


def _pad_to_square(image: Image.Image, size: int) -> Image.Image:
    src = image.convert("RGB")
    width, height = src.size
    if width == 0 or height == 0:
        raise WD14RuntimeError("Invalid image size")

    ratio = min(size / width, size / height)
    new_width = max(1, int(width * ratio))
    new_height = max(1, int(height * ratio))
    resized = src.resize((new_width, new_height), Image.Resampling.BICUBIC)

    canvas = Image.new("RGB", (size, size), (255, 255, 255))
    paste_x = (size - new_width) // 2
    paste_y = (size - new_height) // 2
    canvas.paste(resized, (paste_x, paste_y))
    return canvas


class WD14Tagger:
    def __init__(self, model_path: Path = DEFAULT_MODEL_PATH, tags_path: Path = DEFAULT_TAGS_PATH):
        self.model_path = model_path
        self.tags_path = tags_path
        self._init_lock = Lock()
        self._initialized = False
        self._session: Any | None = None
        self._input_name = ""
        self._output_name = ""
        self._channels_first = False
        self._input_size = 448
        self._tags: list[WD14TagMeta] = []

    def available(self) -> tuple[bool, str]:
        if np is None:
            return False, "numpy is not installed"
        if ort is None:
            return False, "onnxruntime is not installed"
        if not self.model_path.exists():
            return False, f"Missing WD14 model file: {self.model_path}"
        if not self.tags_path.exists():
            return False, f"Missing WD14 tags file: {self.tags_path}"
        return True, "ok"

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return

            ok, reason = self.available()
            if not ok:
                raise WD14RuntimeError(reason)

            assert ort is not None
            self._session = ort.InferenceSession(
                str(self.model_path),
                providers=["CPUExecutionProvider"],
            )
            model_inputs = self._session.get_inputs()
            model_outputs = self._session.get_outputs()
            if not model_inputs or not model_outputs:
                raise WD14RuntimeError("Invalid ONNX model inputs/outputs")

            self._input_name = model_inputs[0].name
            self._output_name = model_outputs[0].name
            shape = model_inputs[0].shape

            # Typical WD14 shapes:
            # - [1, 448, 448, 3] channels-last
            # - [1, 3, 448, 448] channels-first
            if len(shape) == 4 and shape[1] == 3:
                self._channels_first = True
                if isinstance(shape[2], int):
                    self._input_size = int(shape[2])
            elif len(shape) == 4 and shape[-1] == 3:
                self._channels_first = False
                if isinstance(shape[1], int):
                    self._input_size = int(shape[1])

            self._tags = _read_tag_metadata(self.tags_path)
            self._initialized = True

    def _preprocess(self, image_path: str) -> np.ndarray:
        if np is None:
            raise WD14RuntimeError("numpy is not installed")
        with Image.open(image_path) as img:
            squared = _pad_to_square(img, self._input_size)
            array = np.asarray(squared).astype(np.float32)

        # WD14 expects BGR [0,1].
        array = array[:, :, ::-1] / 255.0
        if self._channels_first:
            array = np.transpose(array, (2, 0, 1))
        array = np.expand_dims(array, axis=0)
        return array.astype(np.float32)

    def predict(
        self,
        image_path: str,
        general_threshold: float = 0.35,
        character_threshold: float = 0.85,
        rating_threshold: float = 0.5,
        max_tags: int = 60,
    ) -> WD14PredictResult:
        self._ensure_initialized()
        assert self._session is not None

        tensor = self._preprocess(image_path)
        probs = self._session.run([self._output_name], {self._input_name: tensor})[0]
        if probs.ndim == 2:
            probs = probs[0]

        if len(probs) != len(self._tags):
            raise WD14RuntimeError(
                f"Output length mismatch. model={len(probs)}, tags={len(self._tags)}"
            )

        general_and_character: list[tuple[str, float]] = []
        ratings: list[tuple[str, float]] = []
        for meta, score in zip(self._tags, probs.tolist()):
            if meta.category == 9:
                if score >= rating_threshold:
                    ratings.append((meta.name, score))
                continue

            threshold = character_threshold if meta.category == 4 else general_threshold
            if score >= threshold:
                general_and_character.append((meta.name, score))

        general_and_character.sort(key=lambda x: x[1], reverse=True)
        ratings.sort(key=lambda x: x[1], reverse=True)

        tags = [name for name, _ in general_and_character[:max_tags]]
        rating_names = [name for name, _ in ratings]
        return WD14PredictResult(tags=tags, ratings=rating_names)


_TAGGER = WD14Tagger()


def get_wd14_tagger() -> WD14Tagger:
    return _TAGGER


def get_wd14_status() -> tuple[bool, str]:
    return _TAGGER.available()
