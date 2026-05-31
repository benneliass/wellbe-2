FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/packages/ ./packages/
COPY backend/apps/safety-gate/ ./apps/safety-gate/

RUN uv sync --package wellbe-safety-gate --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/apps/safety-gate/src"
EXPOSE 8005

ARG DEV=false
ENV DEV=${DEV}
CMD if [ "$DEV" = "true" ]; then \
      exec uvicorn wellbe_safety_gate.main:app --host 0.0.0.0 --port 8005 --reload --reload-dir /app/apps/safety-gate/src --reload-dir /app/packages; \
    else \
      exec uvicorn wellbe_safety_gate.main:app --host 0.0.0.0 --port 8005; \
    fi
