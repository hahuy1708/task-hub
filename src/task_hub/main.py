from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from task_hub.core.config import settings
from task_hub.core.exceptions import AppException
from task_hub.database import engine
from task_hub.routers import api_router


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    application.state.redis = redis
    try:
        yield
    finally:
        await redis.aclose()
        await engine.dispose()


app = FastAPI(
    title="TaskHub",
    version="0.1.0",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(AppException)
async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
        headers=getattr(exc, "headers", None),
    )


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
