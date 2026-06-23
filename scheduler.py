from datetime import date
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from task_bot.config import Config
from task_bot.sheets import SheetsStore, Task
from task_bot.deadlines import select_deadline_pings
from task_bot.reporting import build_report

# Папка с картинками-лицами (лежат рядом с этим модулем, в task_bot/)
_FACES_DIR = Path(__file__).parent


def _deadline_message(task: Task, reason: str) -> "tuple[str, str]":
    """По стадии напоминания возвращает (путь к лицу, живой текст-подпись)."""
    if reason == "two_days":
        face = "face2 первое напоминание.jpg"
        text = (
            "Так, без паники 🧘\n\n"
            f"#{task.id} «{task.title}» — дедлайн через 2 дня ({task.deadline}).\n"
            "Времени вагон. Можно даже сначала чаю. Но потом — сделать."
        )
    elif reason == "today":
        face = "face1 напоминание в день дедлайна.jpg"
        text = (
            "А вот и дедлайн подъехал 😏\n\n"
            f"#{task.id} «{task.title}» — это сегодня, дружок.\n"
            "Часики тикают, а задачка сама себя не сделает. "
            "Или сделает? Нет. Не сделает."
        )
    else:  # overdue
        face = "face3 после дедлайна.jpg"
        text = (
            "Не, ну всё нормально 🙂\n\n"
            f"#{task.id} «{task.title}» просто… немножко просрочена. Совсем капельку.\n"
            "Я не злюсь. Я просто сижу тут. И жду. И улыбаюсь :)"
        )
    return str(_FACES_DIR / face), text


def start_scheduler(bot: Bot, config: Config, store: SheetsStore) -> AsyncIOScheduler:
    """
    Creates and starts an AsyncIOScheduler with two jobs:
      1. Daily deadline check — DMs each assignee if their task is due tomorrow or overdue.
      2. Weekly report — posts a summary to the group chat every Monday.
    Both jobs are wrapped in try/except so a failure never crashes the bot.
    Times come from config.daily_check_time / weekly_report_time ("HH:MM").
    """
    scheduler = AsyncIOScheduler()
    # Разбираем время из строки "HH:MM"
    dh, dm = map(int, config.daily_check_time.split(":"))
    wh, wm = map(int, config.weekly_report_time.split(":"))

    async def check_deadlines():
        try:
            today = date.today()
            for task, reason in select_deadline_pings(store.list_tasks(), today):
                chat_id = store.get_user_chat_id(task.assignee)
                if chat_id is None:
                    continue
                face_path, text = _deadline_message(task, reason)
                # Шлём лицо-картинку с живой подписью
                await bot.send_photo(chat_id, FSInputFile(face_path), caption=text)
        except Exception as e:  # планировщик не должен ронять бота
            print(f"[scheduler] check_deadlines error: {e}")

    async def weekly_report():
        try:
            report = build_report(store.list_tasks(), date.today())
            await bot.send_message(config.group_chat_id, report)
        except Exception as e:
            print(f"[scheduler] weekly_report error: {e}")

    # Ежедневная проверка дедлайнов
    scheduler.add_job(check_deadlines, CronTrigger(hour=dh, minute=dm))
    # Еженедельная сводка по понедельникам (day_of_week=0)
    scheduler.add_job(weekly_report, CronTrigger(day_of_week=0, hour=wh, minute=wm))
    scheduler.start()
    return scheduler
