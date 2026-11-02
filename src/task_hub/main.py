from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from task_hub.routers import api_router
from task_hub.services.task import NotFoundError

app = FastAPI(title="TaskHub", version="0.1.0")
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(NotFoundError)
def handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
