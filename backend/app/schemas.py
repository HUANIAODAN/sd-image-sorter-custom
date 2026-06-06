from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    directory: str = Field(min_length=1)
    recursive: bool = True
    max_files: int | None = Field(default=None, ge=1)


class ScanResponse(BaseModel):
    scanned: int
    added: int
    updated: int
    skipped: int
    gallery_id: int | None = None
    gallery_name: str | None = None


class ImageSummary(BaseModel):
    id: int
    gallery_id: int | None = None
    path: str
    name: str
    ext: str
    width: int | None
    height: int | None
    size_bytes: int
    mtime: float
    rating: int
    tags: list[str]
    generator_source: str = "Unknown"
    content_rating: str = "unknown"
    checkpoint_name: str = ""
    lora_names: list[str] = Field(default_factory=list)
    positive_prompt: str = ""
    positive_prompt_zh: str = ""
    steps: int | None = None
    cfg_scale: float | None = None
    sampler: str = ""
    schedule_type: str = ""
    clip_skip: int | None = None


class ImageListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[ImageSummary]


class TagUpdateRequest(BaseModel):
    tags: list[str] = Field(default_factory=list)


class RatingUpdateRequest(BaseModel):
    rating: int = Field(ge=0, le=5)


class MoveImageRequest(BaseModel):
    image_id: int
    target_directory: str = Field(min_length=1)
    strategy: Literal["flat", "first_tag", "rating", "generator", "content_rating"] = "flat"


class MoveImageResponse(BaseModel):
    image_id: int
    old_path: str
    new_path: str


class BatchMoveRequest(BaseModel):
    image_ids: list[int] | None = None
    keyword: str | None = None
    tag: str | None = None
    generator: str | None = None
    content_rating: str | None = None
    checkpoint: str | None = None
    lora: str | None = None
    prompt_keyword: str | None = None
    min_rating: int | None = Field(default=None, ge=0, le=5)
    max_rating: int | None = Field(default=None, ge=0, le=5)
    min_width: int | None = Field(default=None, ge=1)
    max_width: int | None = Field(default=None, ge=1)
    min_height: int | None = Field(default=None, ge=1)
    max_height: int | None = Field(default=None, ge=1)
    aspect_ratio: Literal["square", "landscape", "portrait"] | None = None
    sort_by: str = "newest"
    target_directory: str = Field(min_length=1)
    strategy: Literal["flat", "first_tag", "rating", "generator", "content_rating"] = "flat"


class AutoTagRequest(BaseModel):
    image_id: int


class AutoTagResponse(BaseModel):
    image_id: int
    tags: list[str]
    source: Literal["wd14", "filename_fallback"]
    content_rating: str | None = None


class AutoTagBatchStartRequest(BaseModel):
    image_ids: list[int] | None = None
    only_untagged: bool = True
    general_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    character_threshold: float = Field(default=0.85, ge=0.0, le=1.0)


class AutoTagBatchStartResponse(BaseModel):
    job_id: str
    total: int
    mode: Literal["wd14", "filename_fallback"]
    note: str | None = None


class AutoTagBatchStatusResponse(BaseModel):
    job_id: str
    mode: Literal["wd14", "filename_fallback"]
    status: Literal["pending", "running", "completed", "failed"]
    total: int
    processed: int
    success: int
    failed: int
    skipped: int
    progress: float
    current_image_id: int | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AutoTagRuntimeStatusResponse(BaseModel):
    model_available: bool
    mode: Literal["wd14", "filename_fallback"]
    detail: str


class ErrorResponse(BaseModel):
    detail: str


class ImageDetail(ImageSummary):
    gallery_name: str | None = None
    negative_prompt: str = ""
    vae_name: str = ""
    seed: str = ""
    created_at: datetime
    updated_at: datetime


class GallerySummary(BaseModel):
    id: int
    name: str
    path: str
    image_count: int
    last_scanned_at: datetime | None = None
    generator_breakdown: dict[str, int] = Field(default_factory=dict)


class GalleryListResponse(BaseModel):
    items: list[GallerySummary]


class LibraryValueCount(BaseModel):
    value: str
    count: int


class ImageParseResponse(BaseModel):
    filename: str
    width: int | None = None
    height: int | None = None
    size_bytes: int = 0
    generator_source: str = "Unknown"
    positive_prompt: str = ""
    positive_prompt_zh: str = ""
    negative_prompt: str = ""
    checkpoint_name: str = ""
    lora_names: list[str] = Field(default_factory=list)
    vae_name: str = ""
    seed: str = ""
    steps: int | None = None
    cfg_scale: float | None = None
    sampler: str = ""
    schedule_type: str = ""
    clip_skip: int | None = None
    phash: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ManualSortStartRequest(BaseModel):
    folders: dict[str, str] = Field(default_factory=dict)
    keyword: str | None = None
    tag: str | None = None
    generator: str | None = None
    content_rating: str | None = None
    checkpoint: str | None = None
    lora: str | None = None
    prompt_keyword: str | None = None
    min_rating: int | None = Field(default=None, ge=0, le=5)
    max_rating: int | None = Field(default=None, ge=0, le=5)
    min_width: int | None = Field(default=None, ge=1)
    max_width: int | None = Field(default=None, ge=1)
    min_height: int | None = Field(default=None, ge=1)
    max_height: int | None = Field(default=None, ge=1)
    aspect_ratio: Literal["square", "landscape", "portrait"] | None = None
    sort_by: str = "newest"


class ManualSortActionRequest(BaseModel):
    action: Literal["move", "skip", "undo"]
    folder_key: str | None = None


class PromptLabGenerateRequest(BaseModel):
    selected_tags: list[str] = Field(default_factory=list)
    quality_preset: Literal["high", "medium", "none"] = "high"
    count_tag: str = "1girl"
    include_negative: bool = True
    randomize: bool = False
    seed: int | None = None

