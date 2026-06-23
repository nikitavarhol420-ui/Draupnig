from datetime import date
from task_bot.sheets import Task
from task_bot.reporting import (
    filter_tasks, format_task_card, format_task_list, build_report,
)


def task(**kw):
    base = dict(
        id=1, title="T", description="", assignee="nick", status="todo",
        deadline="", created_at="2026-06-20 10:00", created_by="alex", done_at="",
    )
    base.update(kw)
    return Task(**base)


def test_filter_by_assignee():
    tasks = [task(id=1, assignee="nick"), task(id=2, assignee="alex")]
    assert [t.id for t in filter_tasks(tasks, assignee="nick")] == [1]


def test_filter_by_status():
    tasks = [task(id=1, status="todo"), task(id=2, status="done")]
    assert [t.id for t in filter_tasks(tasks, status="done")] == [2]


def test_format_task_card_contains_key_fields():
    card = format_task_card(task(id=7, title="Бэктест", deadline="2026-07-01"))
    assert "7" in card and "Бэктест" in card and "2026-07-01" in card


def test_format_task_list_empty():
    assert "Нет задач" in format_task_list([])


def test_build_report_buckets():
    today = date(2026, 6, 23)
    tasks = [
        task(id=1, status="in_progress"),
        task(id=2, status="todo", deadline="2026-06-20"),   # просрочено
        task(id=3, status="done", done_at="2026-06-21 12:00"),  # закрыто за 7 дней
        task(id=4, status="done", done_at="2026-06-01 12:00"),  # старое, не считаем
    ]
    report = build_report(tasks, today)
    assert "В работе" in report
    assert "Просрочено" in report
    assert "Закрыто за 7 дней" in report
    # старая закрытая задача (id=4) не попадает в недельную сводку
    assert report.count("#4") == 0
