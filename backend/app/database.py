from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{(DATA_DIR / 'sd_sorter.db').as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_runtime_schema() -> None:
    with engine.begin() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(images)")).fetchall()}
        if "gallery_id" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN gallery_id INTEGER"))
        if "generator_source" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN generator_source TEXT DEFAULT 'Unknown'"))
        if "positive_prompt" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN positive_prompt TEXT"))
        if "negative_prompt" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN negative_prompt TEXT"))
        if "positive_prompt_zh" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN positive_prompt_zh TEXT"))
        if "checkpoint_name" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN checkpoint_name TEXT"))
        if "lora_names" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN lora_names TEXT"))
        if "vae_name" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN vae_name TEXT"))
        if "seed" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN seed TEXT"))
        if "nsfw_score" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN nsfw_score REAL"))
        if "steps" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN steps INTEGER"))
        if "cfg_scale" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN cfg_scale REAL"))
        if "sampler" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN sampler TEXT"))
        if "schedule_type" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN schedule_type TEXT"))
        if "clip_skip" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN clip_skip INTEGER"))
        if "content_rating" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN content_rating TEXT DEFAULT 'unknown'"))
        if "phash" not in columns:
            conn.execute(text("ALTER TABLE images ADD COLUMN phash TEXT"))
