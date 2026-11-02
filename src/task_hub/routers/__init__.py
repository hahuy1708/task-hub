from fastapi import APIRouter

from task_hub.routers.task import router as task_router

api_router = APIRouter()
api_router.include_router(task_router)
