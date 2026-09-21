FROM python:3.12.14-alpine3.24@sha256:c4634f578a412db396771b61b064c6e546c9d6414c7fb5b1b05d5871f1885f7b AS dependencies
COPY --from=ghcr.io/astral-sh/uv:0.12.17@sha256:10787c682e4184e4f290de1171fd4703dc63de99221f10fe1c99002ce7fa9acc /uv /usr/local/bin/uv
WORKDIR /app/backend
ENV UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project --no-build

FROM python:3.12.14-alpine3.24@sha256:c4634f578a412db396771b61b064c6e546c9d6414c7fb5b1b05d5871f1885f7b AS runtime
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH="/opt/venv/bin:$PATH" PYTHONPATH=/app/backend/src:/app
RUN addgroup -g 1000 app && adduser -D -u 1000 -G app app \
    && rm -rf /usr/local/lib/python3.12/site-packages/pip \
        /usr/local/lib/python3.12/site-packages/pip-*.dist-info \
        /usr/local/lib/python3.12/ensurepip \
    && rm -f /usr/local/bin/pip*
COPY --from=dependencies /opt/venv /opt/venv
COPY --chown=app:app backend ./
COPY --chown=app:app evals /app/evals
COPY --chown=app:app data /app/data
COPY --chown=app:app scripts /app/scripts
USER app
EXPOSE 8102
CMD ["uvicorn", "loja_assistente.app:app", "--host", "0.0.0.0", "--port", "8102"]
