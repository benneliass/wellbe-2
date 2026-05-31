FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/packages/ ./packages/
COPY backend/apps/processing-worker/ ./apps/processing-worker/

RUN uv sync --package wellbe-processing-worker --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/apps/processing-worker/src"
EXPOSE 8004

ARG DEV=false
ENV DEV=${DEV}
CMD if [ "$DEV" = "true" ]; then \
      exec uvicorn wellbe_processing_worker.main:app --host 0.0.0.0 --port 8004 --reload --reload-dir /app/apps/processing-worker/src --reload-dir /app/packages; \
    else \
      exec uvicorn wellbe_processing_worker.main:app --host 0.0.0.0 --port 8004; \
    fi
