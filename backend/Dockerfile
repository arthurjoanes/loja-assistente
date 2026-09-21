FROM python:3.12.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /usr/local/bin/uv
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv PATH="/opt/venv/bin:$PATH" PYTHONPATH=/app/backend/src:/app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project
COPY backend ./
COPY evals /app/evals
COPY data /app/data
COPY scripts /app/scripts
RUN useradd --create-home app && chown -R app:app /app
USER app
EXPOSE 8102
CMD ["uvicorn", "loja_assistente.app:app", "--host", "0.0.0.0", "--port", "8102"]
