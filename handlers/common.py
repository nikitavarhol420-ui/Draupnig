from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from task_bot.config import Config
from task_bot.sheets import SheetsStore

HELP_TEXT = (
    "Я бот-менеджер задач Draupnir.\n\n"
    "/new — создать задачу\n"
    "/tasks — список задач (с фильтрами)\n"
    "/task N — карточка задачи N\n"
    "/report — сводка\n"
    "/start — зарегистрироваться для личных уведомлений\n"
    "/help — эта справка"
)


def build_common_router(config: Config, store: SheetsStore) -> Router:
    router = Router()
    # Словарь username -> display_name из конфига участников
    names = {p.username: p.display_name for p in config.participants}

    @router.message(CommandStart())
    async def on_start(message: Message):
        # Берём username из Telegram, fallback — строковый ID
        username = message.from_user.username or str(message.from_user.id)
        # Имя из конфига → Telegram full_name → username
        display_name = names.get(username, message.from_user.full_name or username)
        store.upsert_user(username, message.chat.id, display_name)
        await message.answer(
            f"Готово, {display_name}! Теперь буду присылать тебе личные "
            f"уведомления о задачах.\n\n{HELP_TEXT}"
        )

    @router.message(Command("help"))
    async def on_help(message: Message):
        await message.answer(HELP_TEXT)

    return router
