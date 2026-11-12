from typing import Annotated

from fastapi import Path

from task_hub.core.constants import TASK_ID_MIN

ProjectId = Annotated[int, Path(ge=TASK_ID_MIN)]
WorkspaceId = Annotated[int, Path(ge=TASK_ID_MIN)]
