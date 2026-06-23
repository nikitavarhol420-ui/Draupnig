from datetime import date, datetime
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from task_bot.config import Config
from task_bot.sheets import SheetsStore, Task
from task_bot.deadlines import select_deadline_pings
from task_bot.reporting import build_report, kid, esc, human_date
from task_bot import phrases

# Папка с картинками-лицами и голосовыми (лежат рядом с этим модулем, в task_bot/)
_FACES_DIR = Path(__file__).parent

# Картинка-лицо на каждую стадию напоминания («за 1 день» — та же, что за 2 дня).
# Латинские имена + сжатый jpg: большие png с кириллицей в имени не проходили
# через HTTP-прокси (обрыв upload), сжатый jpg идёт нормально.
_FACE_BY_REASON = {
    "two_days": "two_days.jpg",
    "one_day": "two_days.jpg",
    "today": "today.jpg",
    "overdue": "overdue.jpg",
}
# Голосовое (нарезка из шортса) на каждую стадию («за 1 день» — тот же, что за 2 дня)
_VOICE_BY_REASON = {
    "two_days": "voice_two_days.ogg",
    "one_day": "voice_two_days.ogg",
    "today": "voice_today.ogg",
    "overdue": "voice_overdue.ogg",
}
# Пул мемных фраз на каждую стадию (берётся случайная)
_POOL_BY_REASON = {
    "two_days": phrases.TWO_DAYS,
    "one_day": phrases.ONE_DAY,
    "today": phrases.TODAY,
    "overdue": phrases.OVERDUE,
}


def _deadline_message(task: Task, reason: str, spoiler: bool = False) -> "tuple[str, str]":
    """По стадии напоминания возвращает (путь к лицу, живой текст-подпись).
    Опенер берётся случайно из пула — текст меняется от раза к разу.
    spoiler=True (утренний пинг) прячет подпись под скрытый текст Telegram."""
    title = esc(task.title)
    num = kid(task.id)
    opener = phrases.pick(_POOL_BY_REASON[reason])
    if reason in ("two_days", "one_day"):
        text = f"{opener}\n\n{num} {title}\nдедлайн {human_date(task.deadline)}"
    elif reason == "today":
        text = f"{opener}\n\n{num} {title}"
    else:  # overdue
        text = f"{opener}\n\n{num} {title}\nникогда не поздно"
    if spoiler:
        # Скрытый текст: подпись спрятана за «точками», читается по тапу.
        text = f"<tg-spoiler>{text}</tg-spoiler>"
    return str(_FACES_DIR / _FACE_BY_REASON[reason]), text


def start_scheduler(bot: Bot, config: Config, store: SheetsStore) -> AsyncIOScheduler:
    """
    Creates and starts an AsyncIOScheduler with two jobs:
      1. Daily deadline check — DMs each assignee if their task is due tomorrow or overdue.
      2. Weekly report — posts a summary to the group chat every Monday.
    Both jobs are wrapped in try/except so a failure never crashes the bot.
    Times come from config.daily_check_time / weekly_report_time ("HH:MM").
    """
    scheduler = AsyncIOScheduler()
    # Разбираем время из строк "HH:MM"
    dh, dm = map(int, config.daily_check_time.split(":"))      # утренний прогон (11:00)
    eh, em = map(int, config.evening_today_time.split(":"))    # вечерний прогон (20:00)
    oh, om = map(int, config.overdue_time.split(":"))          # прогон просрочки (20:30)
    wh, wm = map(int, config.weekly_report_time.split(":"))

    async def check_deadlines(reasons: set, spoiler: bool = False):
        """Прогон напоминаний для заданного набора стадий (reasons).
        spoiler=True — подпись прячется под скрытый текст Telegram."""
        try:
            today = date.today()
            for task, reason in select_deadline_pings(store.list_tasks(), today):
                if reason not in reasons:
                    continue
                chat_id = store.get_user_chat_id(task.assignee)
                if chat_id is None:
                    continue
                # Затяжная просрочка (3+ дней) — тоже прячем текст под спойлер
                task_spoiler = spoiler
                if reason == "overdue":
                    try:
                        dl = datetime.strptime(task.deadline, "%Y-%m-%d").date()
                        if (today - dl).days >= 3:
                            task_spoiler = True
                    except ValueError:
                        pass
                face_path, text = _deadline_message(task, reason, spoiler=task_spoiler)
                # Шлём лицо-картинку с живой подписью, следом — голосовое стадии
                await bot.send_photo(chat_id, FSInputFile(face_path), caption=text)
                voice_path = _FACES_DIR / _VOICE_BY_REASON[reason]
                if voice_path.exists():
                    await bot.send_voice(chat_id, FSInputFile(str(voice_path)))
        except Exception as e:  # планировщик не должен ронять бота
            print(f"[scheduler] check_deadlines error: {e}")

    async def weekly_report():
        try:
            report = build_report(store.list_tasks(), date.today())
            await bot.send_message(config.group_chat_id, report)
        except Exception as e:
            print(f"[scheduler] weekly_report error: {e}")

    # Утро (11:00): «за 2 дня» и «в день дедлайна», текст скрыт спойлером
    scheduler.add_job(
        check_deadlines, CronTrigger(hour=dh, minute=dm),
        kwargs={"reasons": {"two_days", "today"}, "spoiler": True},
    )
    # Вечер (20:00): «за 1 день» и «в день дедлайна», текст открыт
    scheduler.add_job(
        check_deadlines, CronTrigger(hour=eh, minute=em),
        kwargs={"reasons": {"one_day", "today"}, "spoiler": False},
    )
    # Просрочка (20:30): каждый день, пока задача не закрыта
    scheduler.add_job(
        check_deadlines, CronTrigger(hour=oh, minute=om),
        kwargs={"reasons": {"overdue"}, "spoiler": False},
    )
    # Еженедельная сводка по понедельникам (day_of_week=0)
    scheduler.add_job(weekly_report, CronTrigger(day_of_week=0, hour=wh, minute=wm))
    scheduler.start()
    return scheduler
