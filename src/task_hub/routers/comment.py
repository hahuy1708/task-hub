from typing import Annotated

from fastapi import APIRouter, Path, status

from task_hub.core.constants import TASK_ID_MIN
from task_hub.dependencies import CommentServiceDep, CurrentUserDep
from task_hub.schemas.comment import CommentCreate, CommentRead

router = APIRouter(tags=["comments"])
CommentId = Annotated[int, Path(ge=TASK_ID_MIN)]


@router.post(
    "/tasks/{task_id}/comments",
    status_code=status.HTTP_201_CREATED,
    summary="Create a task comment",
)
async def create_comment(
    task_id: CommentId,
    data: CommentCreate,
    user: CurrentUserDep,
    service: CommentServiceDep,
) -> CommentRead:
    return CommentRead.model_validate(await service.create_comment(task_id, user, data))


@router.get("/tasks/{task_id}/comments", summary="List task comments")
async def list_comments(
    task_id: CommentId, user: CurrentUserDep, service: CommentServiceDep
) -> list[CommentRead]:
    return [
        CommentRead.model_validate(comment)
        for comment in await service.list_comments(task_id, user)
    ]


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
)
async def delete_comment(
    comment_id: CommentId, user: CurrentUserDep, service: CommentServiceDep
) -> None:
    await service.delete_comment(comment_id, user)
