FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/uv.lock ./uv.lock
COPY backend/packages/ ./packages/
COPY backend/apps/continuity-worker/ ./apps/continuity-worker/

RUN uv sync --frozen --package wellbe-continuity-worker --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/apps/continuity-worker/src"

CMD ["python", "-m", "wellbe_continuity_worker.main"]
