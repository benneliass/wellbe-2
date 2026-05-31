FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/packages/ ./packages/
COPY backend/apps/ingestion-worker/ ./apps/ingestion-worker/

RUN uv sync --package wellbe-ingestion-worker --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8003
CMD ["uvicorn", "wellbe_ingestion_worker.main:app", "--host", "0.0.0.0", "--port", "8003"]
