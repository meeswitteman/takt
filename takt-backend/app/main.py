from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.database import engine, Base
from app.routers import items, contexts, todos, variations
import app.models  # noqa: F401 — ensures all models are registered before create_all

Base.metadata.create_all(bind=engine)

# Voeg is_done kolom toe aan bestaande databases die hem nog niet hebben
with engine.connect() as _conn:
    try:
        _conn.execute(text("ALTER TABLE item ADD COLUMN is_done BOOLEAN NOT NULL DEFAULT 0"))
        _conn.commit()
    except Exception:
        pass  # kolom bestaat al

app = FastAPI(title="Takt API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router)
app.include_router(contexts.router)
app.include_router(todos.router)
app.include_router(variations.router)


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
