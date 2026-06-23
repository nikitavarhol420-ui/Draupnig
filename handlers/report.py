from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from task_bot.sheets import SheetsStore
from task_bot.reporting import build_report


def build_report_router(store: SheetsStore) -> Router:
    """
    Роутер для команды /report — выдаёт сводку прямо сейчас (on-demand),
    в отличие от планировщика, который шлёт её по расписанию каждый понедельник.
    """
    router = Router()

    @router.message(Command("report"))
    async def on_report(message: Message):
        tasks = store.list_tasks()
        text = build_report(tasks, date.today())
        await message.answer(text)

    return router
