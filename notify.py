from aiogram import Bot

from task_bot.config import Config
from task_bot.sheets import SheetsStore, Task


def make_assignment_notifier(bot: Bot, store: SheetsStore, config: Config):
    """
    Returns an async function that DMs the task assignee when a task is assigned.
    If the assignee hasn't done /start (no chat_id), sends a warning to the group chat
    instead of silently dropping the notification — spec §6.
    """
    async def notify_assignment(task: Task) -> None:
        chat_id = store.get_user_chat_id(task.assignee)
        if chat_id is None:
            # Исполнитель не делал /start — сообщаем в групповой чат, чтобы не потерять
            warning = (
                f"⚠️ @{task.assignee} ещё не написал боту /start — "
                f"задача #{task.id} «{task.title}» назначена, "
                f"но личное уведомление не доставлено."
            )
            await bot.send_message(config.group_chat_id, warning)
            return
        text = (f"📌 На тебя назначена задача #{task.id}: {task.title}"
                + (f"\nДедлайн: {task.deadline}" if task.deadline else ""))
        await bot.send_message(chat_id, text)
    return notify_assignment
