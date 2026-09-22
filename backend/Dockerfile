FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
COPY app ./app
COPY config ./config
COPY migrations ./migrations
COPY alembic.ini ./
RUN useradd --create-home app && mkdir -p /app/data && chown -R app:app /app
USER app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
