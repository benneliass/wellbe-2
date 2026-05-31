FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/packages/ ./packages/
COPY backend/apps/api/ ./apps/api/

RUN uv sync --package wellbe-api --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/apps/api/src"
EXPOSE 8001

ARG DEV=false
ENV DEV=${DEV}
CMD if [ "$DEV" = "true" ]; then \
      exec uvicorn wellbe_api.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir /app/apps/api/src --reload-dir /app/packages; \
    else \
      exec uvicorn wellbe_api.main:app --host 0.0.0.0 --port 8001; \
    fi
