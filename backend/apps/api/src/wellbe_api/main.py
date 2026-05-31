"""C13 API & Contract Layer — FastAPI entrypoint stub."""
from fastapi import FastAPI

app = FastAPI(
    title="WellBe API",
    version="0.1.0",
    description="Single external boundary. All surfaces call through here. See docs/architecture/component-map.md C13.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
