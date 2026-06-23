from datetime import date
from task_bot.sheets import Task
from task_bot.deadlines import select_deadline_pings


def task(**kw):
    base = dict(
        id=1, title="T", description="", assignee="nick", status="todo",
        deadline="", created_at="", created_by="alex", done_at="",
    )
    base.update(kw)
    return Task(**base)


def test_tomorrow_is_selected():
    today = date(2026, 6, 23)
    tasks = [task(id=1, deadline="2026-06-24")]
    assert select_deadline_pings(tasks, today) == [(tasks[0], "tomorrow")]


def test_overdue_is_selected():
    today = date(2026, 6, 23)
    tasks = [task(id=1, deadline="2026-06-20")]
    assert select_deadline_pings(tasks, today) == [(tasks[0], "overdue")]


def test_done_and_future_ignored():
    today = date(2026, 6, 23)
    tasks = [
        task(id=1, deadline="2026-06-24", status="done"),  # готово — пропуск
        task(id=2, deadline="2026-07-10"),                 # далеко — пропуск
        task(id=3, deadline=""),                           # нет дедлайна — пропуск
    ]
    assert select_deadline_pings(tasks, today) == []
