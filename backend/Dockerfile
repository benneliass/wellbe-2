FROM python:3.13-slim AS base
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install uv

FROM base AS deps
COPY backend/pyproject.toml backend/uv.lock* ./
COPY backend/packages/ ./packages/
COPY backend/apps/ ./apps/
RUN uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev

FROM base AS runtime
COPY --from=deps /app/.venv /app/.venv
COPY backend/packages/ ./packages/
COPY backend/apps/ ./apps/
ENV PATH="/app/.venv/bin:$PATH"
