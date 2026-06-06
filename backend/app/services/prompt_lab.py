from __future__ import annotations

import random
import re
from collections import Counter, defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Image, Tag, image_tags

QUALITY_PRESETS = {
    "high": ["masterpiece", "best quality", "very aesthetic", "absurdres"],
    "medium": ["best quality", "high quality"],
    "none": [],
}

NEGATIVE_PRESETS = {
    "high": "worst quality, low quality, blurry, bad anatomy, bad hands, extra fingers, watermark, text, jpeg artifacts",
    "medium": "worst quality, low quality, blurry, watermark, text",
    "none": "",
}

CATEGORY_HINTS = {
    "character": ("girl", "boy", "solo", "character", "idol", "hero"),
    "style": ("style", "cinematic", "illustration", "anime", "realistic", "photorealistic"),
    "pose": ("sitting", "standing", "pose", "looking", "hands", "smile"),
    "background": ("background", "sky", "street", "room", "forest", "city", "night", "day"),
    "outfit": ("dress", "shirt", "skirt", "jacket", "uniform", "armor", "kimono"),
}


def categorize_tag(tag: str) -> str:
    lowered = tag.lower()
    for category, hints in CATEGORY_HINTS.items():
        if any(hint in lowered for hint in hints):
            return category
    return "general"


def get_library_stats(db: Session, *, limit: int = 200) -> dict:
    tag_rows = db.execute(
        select(Tag.name, func.count(image_tags.c.image_id))
        .join(image_tags, image_tags.c.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(func.count(image_tags.c.image_id).desc(), Tag.name.asc())
        .limit(limit)
    ).all()

    prompt_counter: Counter[str] = Counter()
    lora_counter: Counter[str] = Counter()
    for image in db.execute(select(Image.positive_prompt, Image.lora_names)).all():
        prompt = image[0] or ""
        for token in [part.strip().lower() for part in re.split(r"[,\\n]+", prompt) if part.strip()]:
            if len(token) >= 3:
                prompt_counter[token] += 1

        loras = image[1] or ""
        for token in [part.strip() for part in loras.split(",") if part.strip()]:
            lora_counter[token] += 1

    grouped_tags: dict[str, list[dict[str, int | str]]] = defaultdict(list)
    for name, count in tag_rows:
        grouped_tags[categorize_tag(name)].append({"value": name, "count": count})

    return {
        "tags": [{"value": name, "count": count} for name, count in tag_rows],
        "prompts": [{"value": value, "count": count} for value, count in prompt_counter.most_common(limit)],
        "loras": [{"value": value, "count": count} for value, count in lora_counter.most_common(limit)],
        "categories": grouped_tags,
    }


def generate_prompt(
    db: Session,
    *,
    selected_tags: list[str],
    quality_preset: str = "high",
    count_tag: str = "1girl",
    include_negative: bool = True,
    randomize: bool = False,
    seed: int | None = None,
) -> dict:
    rng = random.Random(seed)
    library = get_library_stats(db, limit=300)
    used: list[str] = []

    for tag in QUALITY_PRESETS.get(quality_preset, QUALITY_PRESETS["high"]):
        if tag not in used:
            used.append(tag)

    if count_tag and count_tag not in used:
        used.append(count_tag)
        if count_tag in {"1girl", "1boy"} and "solo" not in used:
            used.append("solo")

    for tag in selected_tags:
        normalized = tag.strip()
        if normalized and normalized not in used:
            used.append(normalized)

    if randomize or not selected_tags:
        for category in ("character", "outfit", "pose", "background", "style"):
            pool = library["categories"].get(category, [])
            if not pool:
                continue
            chosen = rng.choice(pool)["value"]
            if chosen not in used:
                used.append(chosen)

    positive_prompt = ", ".join(used)
    negative_prompt = NEGATIVE_PRESETS.get(quality_preset, NEGATIVE_PRESETS["high"]) if include_negative else ""

    return {
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "tags_used": used,
        "library": library,
    }
