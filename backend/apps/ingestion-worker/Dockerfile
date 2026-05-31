FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/packages/ ./packages/
COPY backend/apps/ingestion-worker/ ./apps/ingestion-worker/

RUN uv sync --package wellbe-ingestion-worker --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/apps/ingestion-worker/src"
EXPOSE 8003

ARG DEV=false
ENV DEV=${DEV}
CMD if [ "$DEV" = "true" ]; then \
      exec uvicorn wellbe_ingestion_worker.main:app --host 0.0.0.0 --port 8003 --reload --reload-dir /app/apps/ingestion-worker/src --reload-dir /app/packages; \
    else \
      exec uvicorn wellbe_ingestion_worker.main:app --host 0.0.0.0 --port 8003; \
    fi
