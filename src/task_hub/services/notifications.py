import logging
from typing import Protocol

logger = logging.getLogger("task_hub.notifications")


class TaskNotifier(Protocol):
    def task_assigned(self, *, to_email: str, task_id: int, title: str) -> None: ...


def send_task_assigned_email(to_email: str, task_id: int, title: str) -> None:
    # shortcut: chưa có SMTP, chỉ ghi log. Thay bằng SMTP client khi deploy.
    logger.info(
        "Task assigned email to=%s task_id=%s title=%s", to_email, task_id, title
    )
