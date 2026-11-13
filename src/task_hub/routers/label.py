from typing import Annotated

from fastapi import APIRouter, Path, status

from task_hub.core.constants import TASK_ID_MIN
from task_hub.dependencies import CurrentUserDep, LabelServiceDep
from task_hub.routers.types import ProjectId
from task_hub.schemas.label import LabelCreate, LabelRead, LabelUpdate

router = APIRouter(tags=["labels"])
LabelId = Annotated[int, Path(ge=TASK_ID_MIN)]


@router.post(
    "/projects/{project_id}/labels",
    status_code=status.HTTP_201_CREATED,
    summary="Create a project label",
)
async def create_label(
    project_id: ProjectId,
    data: LabelCreate,
    user: CurrentUserDep,
    service: LabelServiceDep,
) -> LabelRead:
    return LabelRead.model_validate(await service.create_label(project_id, user, data))


@router.get("/projects/{project_id}/labels", summary="List project labels")
async def list_labels(
    project_id: ProjectId, user: CurrentUserDep, service: LabelServiceDep
) -> list[LabelRead]:
    return [
        LabelRead.model_validate(label)
        for label in await service.list_labels(project_id, user)
    ]


@router.patch("/labels/{label_id}", summary="Update a label")
async def update_label(
    label_id: LabelId,
    data: LabelUpdate,
    user: CurrentUserDep,
    service: LabelServiceDep,
) -> LabelRead:
    return LabelRead.model_validate(await service.update_label(label_id, user, data))


@router.delete(
    "/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a label",
)
async def delete_label(
    label_id: LabelId, user: CurrentUserDep, service: LabelServiceDep
) -> None:
    await service.delete_label(label_id, user)


@router.post(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Attach a label to a task",
)
async def attach_label(
    task_id: LabelId,
    label_id: LabelId,
    user: CurrentUserDep,
    service: LabelServiceDep,
) -> None:
    await service.attach_label(task_id, label_id, user)


@router.delete(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Detach a label from a task",
)
async def detach_label(
    task_id: LabelId,
    label_id: LabelId,
    user: CurrentUserDep,
    service: LabelServiceDep,
) -> None:
    await service.detach_label(task_id, label_id, user)
