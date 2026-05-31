FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/packages/ ./packages/
COPY backend/apps/audit-service/ ./apps/audit-service/

RUN uv sync --package wellbe-audit-service --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/apps/audit-service/src:/app/packages/c12_audit/src"
EXPOSE 8006

ARG DEV=false
ENV DEV=${DEV}
CMD if [ "$DEV" = "true" ]; then \
      exec uvicorn wellbe_audit_service.main:app --host 0.0.0.0 --port 8006 --reload --reload-dir /app/apps/audit-service/src --reload-dir /app/packages; \
    else \
      exec uvicorn wellbe_audit_service.main:app --host 0.0.0.0 --port 8006; \
    fi
