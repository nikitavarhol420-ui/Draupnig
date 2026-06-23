import os
from dataclasses import dataclass
from dotenv import load_dotenv


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


def load_config() -> Config:
    load_dotenv()  # подхватит .env, если он есть рядом
    return Config(
        bot_token=os.environ["BOT_TOKEN"],
        spreadsheet_id=os.environ["SPREADSHEET_ID"],
        group_chat_id=int(os.environ["GROUP_CHAT_ID"]),
        google_credentials=os.environ["GOOGLE_CREDENTIALS"],
        participants=_parse_participants(os.environ["PARTICIPANTS"]),
        daily_check_time=os.environ["DAILY_CHECK_TIME"],
        weekly_report_time=os.environ["WEEKLY_REPORT_TIME"],
    )
