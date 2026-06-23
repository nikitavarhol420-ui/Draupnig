import asyncio

from aiogram import Bot, Dispatcher

from task_bot.config import load_config
from task_bot.sheets import SheetsStore
from task_bot.handlers.common import build_common_router
from task_bot.handlers.report import build_report_router
from task_bot.handlers.tasks import build_tasks_router
from task_bot.notify import make_assignment_notifier
from task_bot.scheduler import start_scheduler


async def main():
    # Загружаем конфиг из .env (токен, таблица, участники и т.д.)
    config = load_config()

    # Подключаемся к Google Sheets — единственное «хранилище» бота
    store = SheetsStore(config.google_credentials, config.spreadsheet_id)

    # Создаём объект бота и диспетчер aiogram
    bot = Bot(config.bot_token)
    dp = Dispatcher()

    # Notifier — функция, которая пишет исполнителю в личку при назначении;
    # если исполнитель не делал /start — шлём предупреждение в группу (spec §6).
    notifier = make_assignment_notifier(bot, store, config)

    # Регистрируем роутеры (порядок важен: common — /start и /help, tasks — всё остальное)
    dp.include_router(build_common_router(config, store))
    dp.include_router(build_report_router(store))
    dp.include_router(build_tasks_router(config, store, notifier))

    # Запускаем планировщик фоновых задач (дедлайны + еженедельная сводка)
    start_scheduler(bot, config, store)

    print("Бот запущен. Ctrl+C для остановки.")
    # Запускаем long polling — бот «слушает» Telegram
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
