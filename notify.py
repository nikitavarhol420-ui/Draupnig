from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile

from task_bot.config import Config
from task_bot.sheets import SheetsStore, Task
from task_bot.reporting import kid, esc, human_date

# Лицо «когда выдают задачу» (хитрый прищур) — лежит в папке task_bot/
_ASSIGN_FACE = str(Path(__file__).parent / "face1 напоминание в день дедлайна.jpg")


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
            text = (f"Тебе задачка\n\n{kid(task.id)} {esc(task.title)}"
                    + (f"\nдедлайн {human_date(task.deadline)}" if task.deadline else ""))
            await bot.send_photo(chat_id, FSInputFile(_ASSIGN_FACE), caption=text)
        except Exception as e:
            print(f"[notify] error: {e}")
    return notify_assignment
