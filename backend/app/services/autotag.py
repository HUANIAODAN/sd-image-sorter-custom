import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Image, Tag
from .wd14 import WD14RuntimeError, get_wd14_status, get_wd14_tagger


def guess_tags_from_filename(file_path: str) -> list[str]:
    name = Path(file_path).stem.lower()
    tokens = re.split(r"[_\-\s\.\(\)\[\]]+", name)
    stopwords = {"img", "image", "untitled", "final", "edit", "copy", "v1", "v2"}
    tags = [token for token in tokens if len(token) > 2 and token not in stopwords]
    return list(dict.fromkeys(tags))[:16]


def normalize_content_rating(rating_names: list[str]) -> str | None:
    normalized = {item.strip().lower().replace(" ", "_") for item in rating_names if item and item.strip()}
    for candidate in ("explicit", "questionable", "sensitive", "general"):
        if candidate in normalized:
            return candidate
    return None


def infer_content_rating_from_tags(tags: list[str]) -> str | None:
    normalized = {tag.strip().lower().replace(" ", "_") for tag in tags if tag and tag.strip()}
    if {"explicit", "nsfw"} & normalized:
        return "explicit"
    if {"questionable", "revealing", "suggestive"} & normalized:
        return "questionable"
    if {"sensitive", "bikini", "underwear", "lingerie"} & normalized:
        return "sensitive"
    if normalized:
        return "general"
    return None


def generate_tags_for_image(
    file_path: str,
    general_threshold: float = 0.35,
    character_threshold: float = 0.85,
) -> tuple[list[str], str, str | None]:
    ok, _reason = get_wd14_status()
    if ok:
        try:
            prediction = get_wd14_tagger().predict(
                image_path=file_path,
                general_threshold=general_threshold,
                character_threshold=character_threshold,
            )
            rating = normalize_content_rating(prediction.ratings)
            if prediction.tags:
                return prediction.tags, "wd14", rating or infer_content_rating_from_tags(prediction.tags)
        except (WD14RuntimeError, OSError, ValueError):
            pass

    tags = guess_tags_from_filename(file_path)
    return tags, "filename_fallback", infer_content_rating_from_tags(tags)


def apply_tags(db: Session, image: Image, tags: list[str], content_rating: str | None = None) -> list[str]:
    clean_tags = [tag.strip().lower() for tag in tags if tag.strip()]
    clean_tags = list(dict.fromkeys(clean_tags))
    tag_models = []
    for tag in clean_tags:
        model = db.execute(select(Tag).where(Tag.name == tag)).scalar_one_or_none()
        if model is None:
            model = Tag(name=tag)
            db.add(model)
            db.flush()
        tag_models.append(model)

    image.tags = tag_models
    if content_rating:
        image.content_rating = content_rating
    db.commit()
    return clean_tags
