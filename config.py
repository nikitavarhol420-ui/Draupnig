import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Папка пакета (task_bot/) — относительно неё ищем .env и ключ, чтобы не
# зависеть от рабочей директории (важно для запуска как сервиса).
_HERE = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Participant:
    username: str
    display_name: str


@dataclass(frozen=True)
class Config:
    bot_token: str
    spreadsheet_id: str
    group_chat_id: int
    google_credentials: str
    participants: list[Participant]
    daily_check_time: str          # утренний прогон (11:00): «за 2 дня» и «в день», текст скрыт спойлером
    evening_today_time: str        # вечерний прогон (20:00): «за 1 день» и «в день»
    overdue_time: str              # прогон просрочки (20:30): каждый день, пока не закрыта
    weekly_report_time: str
    # HTTP-прокси для выхода к api.telegram.org (нужен на серверах в РФ, где
    # Telegram заблокирован). На маке не задан — бот ходит напрямую.
    bot_proxy: str | None


def _parse_participants(raw: str) -> list[Participant]:
    # Формат "user:Имя,user2:Имя2" -> список Participant
    result = []
    for chunk in raw.split(","):
        username, display_name = chunk.split(":", 1)
        result.append(Participant(username.strip(), display_name.strip()))
    return result


def _resolve_credentials(raw: str) -> str:
    # Путь к ключу: если относительный — считаем его от корня проекта (на уровень
    # выше task_bot/), иначе берём как есть.
    p = Path(raw)
    if not p.is_absolute():
        candidate = _HERE.parent / raw          # run_root / "task_bot/service_account.json"
        if candidate.exists():
            return str(candidate)
        # запасной вариант — рядом с config.py
        return str(_HERE / Path(raw).name)
    return raw


def load_config() -> Config:
    load_dotenv(_HERE / ".env")  # грузим .env рядом с пакетом, не полагаясь на cwd
    return Config(
        bot_token=os.environ["BOT_TOKEN"],
        spreadsheet_id=os.environ["SPREADSHEET_ID"],
        group_chat_id=int(os.environ["GROUP_CHAT_ID"]),
        google_credentials=_resolve_credentials(os.environ["GOOGLE_CREDENTIALS"]),
        participants=_parse_participants(os.environ["PARTICIPANTS"]),
        daily_check_time=os.environ["DAILY_CHECK_TIME"],
        # Вечерний и просроченный прогоны: дефолты 20:00 / 20:30, если в .env не заданы.
        evening_today_time=os.environ.get("EVENING_TODAY_TIME", "20:00"),
        overdue_time=os.environ.get("OVERDUE_TIME", "20:30"),
        weekly_report_time=os.environ["WEEKLY_REPORT_TIME"],
        # Опционально: пусто/нет переменной -> None -> прямое соединение.
        bot_proxy=os.environ.get("BOT_PROXY") or None,
    )
