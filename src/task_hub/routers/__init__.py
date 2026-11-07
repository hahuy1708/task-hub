from fastapi import APIRouter, Depends

from task_hub.dependencies import get_current_user
from task_hub.routers.auth import router as auth_router
from task_hub.routers.task import router as task_router
from task_hub.routers.user import router as user_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(user_router, prefix="/users")
api_router.include_router(task_router, dependencies=[Depends(get_current_user)])
