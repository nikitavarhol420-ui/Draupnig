import os
from task_bot.config import load_config, Participant


def test_load_config_parses_participants(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "token123")
    monkeypatch.setenv("SPREADSHEET_ID", "sheet123")
    monkeypatch.setenv("GROUP_CHAT_ID", "-1001234567890")
    monkeypatch.setenv("GOOGLE_CREDENTIALS", "creds.json")
    monkeypatch.setenv("PARTICIPANTS", "nick:Ник,alex:Алекс,maria:Мария")
    monkeypatch.setenv("DAILY_CHECK_TIME", "09:00")
    monkeypatch.setenv("WEEKLY_REPORT_TIME", "09:00")

    cfg = load_config()

    assert cfg.bot_token == "token123"
    assert cfg.group_chat_id == -1001234567890
    assert cfg.participants == [
        Participant("nick", "Ник"),
        Participant("alex", "Алекс"),
        Participant("maria", "Мария"),
    ]
