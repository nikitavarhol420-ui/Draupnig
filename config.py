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
    daily_check_time: str
    weekly_report_time: str


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
        weekly_report_time=os.environ["WEEKLY_REPORT_TIME"],
    )
