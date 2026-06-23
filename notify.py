from aiogram import Bot

from task_bot.config import Config
from task_bot.sheets import SheetsStore, Task
from task_bot.reporting import kid, esc, human_date


def make_assignment_notifier(bot: Bot, store: SheetsStore, config: Config):
    """
    Returns an async function that DMs the task assignee when a task is assigned.
    If the assignee hasn't done /start (no chat_id), sends a warning to the group chat
    instead of silently dropping the notification — spec §6.
    """
    async def notify_assignment(task: Task) -> None:
        try:
            chat_id = store.get_user_chat_id(task.assignee)
            if chat_id is None:
                # Исполнитель не делал /start — сообщаем в групповой чат, чтобы не потерять
                warning = (
                    f"⚠️ @{esc(task.assignee)} ещё не написал боту /start — "
                    f"задача {kid(task.id)} {esc(task.title)} назначена, "
                    f"но личное уведомление не доставлено."
                )
                await bot.send_message(config.group_chat_id, warning)
                return
            text = (f"📌 На тебя назначена задача {kid(task.id)}: <b>{esc(task.title)}</b>"
                    + (f"\n<b>Дедлайн:</b> {human_date(task.deadline)}" if task.deadline else ""))
            await bot.send_message(chat_id, text)
        except Exception as e:
            print(f"[notify] error: {e}")
    return notify_assignment
