FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/packages/ ./packages/
COPY backend/apps/notification-worker/ ./apps/notification-worker/

RUN uv sync --package wellbe-notification-worker --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/apps/notification-worker/src"

CMD ["python", "-m", "wellbe_notification_worker.main"]
