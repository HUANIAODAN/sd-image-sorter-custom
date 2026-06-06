from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine, ensure_runtime_schema
from .models import Base
from .routers.actions import router as actions_router
from .routers.images import router as images_router
from .routers.tools import router as tools_router
from .routers.aesthetic import router as aesthetic_router
from .routers.clip_search import router as clip_router
from .routers.obfuscate import router as obfuscate_router
from .routers.wd14_extended import router as wd14_extended_router

app = FastAPI(title="SD Image Sorter Enhanced", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(images_router)
app.include_router(actions_router)
app.include_router(tools_router)
app.include_router(aesthetic_router)
app.include_router(clip_router)
app.include_router(obfuscate_router)
app.include_router(wd14_extended_router)

frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
