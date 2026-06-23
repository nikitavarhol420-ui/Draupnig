from aiogram import Bot

from task_bot.sheets import SheetsStore, Task


def make_assignment_notifier(bot: Bot, store: SheetsStore):
    """
    Returns an async function that DMs the task assignee when a task is assigned.
    Silently skips if the assignee has not done /start (no chat_id in store).
    """
    async def notify_assignment(task: Task) -> None:
        chat_id = store.get_user_chat_id(task.assignee)
        if chat_id is None:
            return  # исполнитель не делал /start — пропускаем
        text = (f"📌 На тебя назначена задача #{task.id}: {task.title}"
                + (f"\nДедлайн: {task.deadline}" if task.deadline else ""))
        await bot.send_message(chat_id, text)
    return notify_assignment
