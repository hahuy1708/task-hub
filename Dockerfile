FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Cài dependency trước để layer này được cache, chỉ chạy lại khi lock đổi.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --system --create-home app
USER app

EXPOSE 8000

# exec để uvicorn nhận SIGTERM trực tiếp khi docker stop.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn task_hub.main:app --host 0.0.0.0 --port 8000"]
