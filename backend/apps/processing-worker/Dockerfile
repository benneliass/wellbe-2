FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Local OCR for image-only documents (ocr.py). Health data never leaves the host.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/uv.lock ./uv.lock
COPY backend/packages/ ./packages/
COPY backend/apps/processing-worker/ ./apps/processing-worker/

RUN uv sync --frozen --package wellbe-processing-worker --no-dev

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
