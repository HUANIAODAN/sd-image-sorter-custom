from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

image_tags = Table(
    "image_tags",
    Base.metadata,
    Column("image_id", Integer, ForeignKey("images.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    UniqueConstraint("image_id", "tag_id", name="uq_image_tag"),
)


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    gallery_id = Column(Integer, ForeignKey("galleries.id", ondelete="SET NULL"), nullable=True, index=True)
    path = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    ext = Column(String, index=True, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)
    mtime = Column(Float, nullable=False, default=0.0)
    rating = Column(Integer, nullable=False, default=0)
    generator_source = Column(String, nullable=False, default="Unknown", index=True)
    positive_prompt = Column(Text, nullable=True)
    negative_prompt = Column(Text, nullable=True)
    positive_prompt_zh = Column(Text, nullable=True)
    checkpoint_name = Column(String, nullable=True)
    lora_names = Column(Text, nullable=True)
    vae_name = Column(String, nullable=True)
    seed = Column(String, nullable=True)
    nsfw_score = Column(Float, nullable=True)
    steps = Column(Integer, nullable=True)
    cfg_scale = Column(Float, nullable=True)
    sampler = Column(String, nullable=True)
    schedule_type = Column(String, nullable=True)
    clip_skip = Column(Integer, nullable=True)
    content_rating = Column(String, nullable=False, default="unknown", index=True)
    phash = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    gallery = relationship("Gallery", back_populates="images")
    tags = relationship("Tag", secondary=image_tags, back_populates="images")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    images = relationship("Image", secondary=image_tags, back_populates="tags")


class Gallery(Base):
    __tablename__ = "galleries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    path = Column(String, unique=True, nullable=False, index=True)
    image_count = Column(Integer, nullable=False, default=0)
    last_scanned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    images = relationship("Image", back_populates="gallery")
