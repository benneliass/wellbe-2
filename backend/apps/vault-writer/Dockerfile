FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml ./pyproject.toml
COPY backend/packages/ ./packages/
COPY backend/apps/vault-writer/ ./apps/vault-writer/

RUN uv sync --package wellbe-vault-writer --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/apps/vault-writer/src"
EXPOSE 8002
CMD ["uvicorn", "wellbe_vault_writer.main:app", "--host", "0.0.0.0", "--port", "8002"]
