import logging

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from task_hub.core.constants import TASK_LIST_CACHE_TTL_SECONDS
from task_hub.models.enums import TaskPriority, TaskStatus
from task_hub.schemas.page import Page
from task_hub.schemas.task import TaskRead

logger = logging.getLogger("task_hub.cache")


def task_list_key(project_id: int) -> str:
    return f"project:{project_id}:tasks"


def task_list_field(
    *,
    status: TaskStatus | None,
    priority: TaskPriority | None,
    assignee_id: int | None,
    skip: int,
    limit: int,
) -> str:
    return "|".join(
        [
            f"status={status or '*'}",
            f"priority={priority or '*'}",
            f"assignee={assignee_id or '*'}",
            f"skip={skip}",
            f"limit={limit}",
        ]
    )


class TaskListCache:
    """Cache-aside cho danh sách task của một project.

    Mỗi project là một hash Redis. Field là bộ lọc cộng phân trang, value là JSON
    của Page[TaskRead]. Lỗi Redis được ghi log và bỏ qua để API vẫn đọc database.
    """

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def get(self, project_id: int, field: str) -> Page[TaskRead] | None:
        try:
            raw = await self.redis.hget(task_list_key(project_id), field)
        except RedisError:
            logger.warning("Task list cache unavailable on read")
            return None
        if raw is None:
            return None
        try:
            return Page[TaskRead].model_validate_json(raw)
        except ValidationError:
            logger.warning("Ignoring malformed task list cache entry")
            return None

    async def set(self, project_id: int, field: str, page: Page[TaskRead]) -> None:
        key = task_list_key(project_id)
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.hset(key, field, page.model_dump_json())
                pipe.expire(key, TASK_LIST_CACHE_TTL_SECONDS)
                await pipe.execute()
        except RedisError:
            logger.warning("Task list cache unavailable on write")

    async def invalidate(self, project_id: int) -> None:
        try:
            await self.redis.delete(task_list_key(project_id))
        except RedisError:
            logger.warning("Task list cache unavailable on invalidate")
