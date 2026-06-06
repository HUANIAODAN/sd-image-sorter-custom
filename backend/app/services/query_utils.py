from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Query

from ..models import Image, Tag, image_tags


def parse_csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return list(dict.fromkeys(part.strip().lower() for part in value.split(",") if part.strip()))


def prompt_length_expr():
    return func.length(func.coalesce(Image.positive_prompt, ""))


def tag_count_expr():
    return (
        select(func.count(image_tags.c.tag_id))
        .where(image_tags.c.image_id == Image.id)
        .scalar_subquery()
    )


def build_image_filters(
    *,
    keyword: str | None = None,
    tags: str | None = None,
    generators: str | None = None,
    content_ratings: str | None = None,
    checkpoints: str | None = None,
    loras: str | None = None,
    prompt_keyword: str | None = None,
    min_rating: int | None = None,
    max_rating: int | None = None,
    min_width: int | None = None,
    max_width: int | None = None,
    min_height: int | None = None,
    max_height: int | None = None,
    aspect_ratio: str | None = None,
    gallery_id: int | None = None,
) -> list:
    filters = []
    if gallery_id is not None:
        filters.append(Image.gallery_id == gallery_id)

    if keyword:
        text = f"%{keyword.strip()}%"
        filters.append(
            or_(
                Image.name.ilike(text),
                Image.positive_prompt.ilike(text),
                Image.checkpoint_name.ilike(text),
                Image.lora_names.ilike(text),
                Image.path.ilike(text),
            )
        )

    if prompt_keyword:
        text = f"%{prompt_keyword.strip()}%"
        filters.append(
            or_(
                Image.positive_prompt.ilike(text),
                Image.negative_prompt.ilike(text),
                Image.positive_prompt_zh.ilike(text),
            )
        )

    generator_values = [value for value in parse_csv_list(generators)]
    if generator_values:
        filters.append(func.lower(Image.generator_source).in_(generator_values))

    content_rating_values = [value for value in parse_csv_list(content_ratings)]
    if content_rating_values:
        filters.append(func.lower(Image.content_rating).in_(content_rating_values))

    checkpoint_values = [value for value in parse_csv_list(checkpoints)]
    if checkpoint_values:
        filters.append(or_(*[Image.checkpoint_name.ilike(f"%{value}%") for value in checkpoint_values]))

    lora_values = [value for value in parse_csv_list(loras)]
    if lora_values:
        filters.append(or_(*[Image.lora_names.ilike(f"%{value}%") for value in lora_values]))

    tag_values = [value for value in parse_csv_list(tags)]
    for value in tag_values:
        filters.append(Image.tags.any(Tag.name == value))

    if min_rating is not None:
        filters.append(Image.rating >= min_rating)
    if max_rating is not None:
        filters.append(Image.rating <= max_rating)
    if min_width is not None:
        filters.append(Image.width >= min_width)
    if max_width is not None:
        filters.append(Image.width <= max_width)
    if min_height is not None:
        filters.append(Image.height >= min_height)
    if max_height is not None:
        filters.append(Image.height <= max_height)

    if aspect_ratio == "square":
        filters.append(Image.width.is_not(None))
        filters.append(Image.height.is_not(None))
        filters.append(func.abs(Image.width - Image.height) <= ((Image.width + Image.height) / 2.0) * 0.08)
    elif aspect_ratio == "landscape":
        filters.append(Image.width.is_not(None))
        filters.append(Image.height.is_not(None))
        filters.append(Image.width > Image.height * 1.05)
    elif aspect_ratio == "portrait":
        filters.append(Image.width.is_not(None))
        filters.append(Image.height.is_not(None))
        filters.append(Image.height > Image.width * 1.05)

    return filters


def apply_sort(query: Query, sort_by: str | None):
    sort_key = (sort_by or "newest").strip().lower()
    prompt_len = prompt_length_expr()
    tag_count = tag_count_expr()

    sort_map = {
        "newest": [Image.mtime.desc(), Image.id.desc()],
        "oldest": [Image.mtime.asc(), Image.id.asc()],
        "name_asc": [func.lower(Image.name).asc(), Image.id.desc()],
        "name_desc": [func.lower(Image.name).desc(), Image.id.desc()],
        "rating_desc": [Image.rating.desc(), Image.id.desc()],
        "rating_asc": [Image.rating.asc(), Image.id.desc()],
        "generator_asc": [func.lower(Image.generator_source).asc(), Image.id.desc()],
        "generator_desc": [func.lower(Image.generator_source).desc(), Image.id.desc()],
        "checkpoint_asc": [func.lower(func.coalesce(Image.checkpoint_name, "")).asc(), Image.id.desc()],
        "checkpoint_desc": [func.lower(func.coalesce(Image.checkpoint_name, "")).desc(), Image.id.desc()],
        "prompt_length_desc": [prompt_len.desc(), Image.id.desc()],
        "prompt_length_asc": [prompt_len.asc(), Image.id.desc()],
        "tag_count_desc": [tag_count.desc(), Image.id.desc()],
        "tag_count_asc": [tag_count.asc(), Image.id.desc()],
        "size_desc": [Image.size_bytes.desc(), Image.id.desc()],
        "size_asc": [Image.size_bytes.asc(), Image.id.desc()],
    }
    return query.order_by(*sort_map.get(sort_key, sort_map["newest"]))
