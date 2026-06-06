from __future__ import annotations

from pathlib import Path

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Image as ImageModel


def compute_dhash(image_path: str | Path, hash_size: int = 8) -> str:
    with Image.open(image_path) as img:
        grayscale = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(grayscale.getdata())

    rows = [pixels[index : index + hash_size + 1] for index in range(0, len(pixels), hash_size + 1)]
    bits: list[str] = []
    for row in rows:
        for left, right in zip(row, row[1:]):
            bits.append("1" if left > right else "0")

    return f"{int(''.join(bits), 2):016x}"


def hamming_distance(hash_a: str, hash_b: str) -> int:
    return (int(hash_a, 16) ^ int(hash_b, 16)).bit_count()


def ensure_image_hash(db: Session, image: ImageModel) -> str | None:
    if image.phash:
        return image.phash

    path = Path(image.path)
    if not path.exists():
        return None

    image.phash = compute_dhash(path)
    db.commit()
    db.refresh(image)
    return image.phash


def find_similar_images(
    db: Session,
    *,
    source_hash: str,
    exclude_image_id: int | None = None,
    limit: int = 24,
) -> list[tuple[ImageModel, int]]:
    rows = (
        db.execute(select(ImageModel).options(selectinload(ImageModel.tags)).where(ImageModel.phash.is_not(None)))
        .scalars()
        .all()
    )

    ranked: list[tuple[ImageModel, int]] = []
    for image in rows:
        if exclude_image_id is not None and image.id == exclude_image_id:
            continue
        if not image.phash:
            continue
        ranked.append((image, hamming_distance(source_hash, image.phash)))

    ranked.sort(key=lambda item: (item[1], -item[0].mtime, item[0].id))
    return ranked[:limit]
