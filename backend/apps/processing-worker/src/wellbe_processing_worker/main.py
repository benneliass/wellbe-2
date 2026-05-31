"""C4 Processing Worker: Dramatiq lightweight extraction jobs."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from wellbe_processing_worker.config import ProcessingWorkerSettings


@asynccontextmanager
async def lifespan(app: FastAPI):
    import wellbe_processing_worker.tasks  # noqa: F401 — registers Dramatiq actors
    yield


settings = ProcessingWorkerSettings()
app = FastAPI(title=settings.service_name, lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
