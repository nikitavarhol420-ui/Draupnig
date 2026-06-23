from datetime import date, datetime, timedelta

from task_bot.sheets import Task


def _parse_date(s: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(s, "%Y-%m-%d").date()


def select_deadline_pings(tasks: list[Task], today: date) -> list[tuple[Task, str]]:
    """
    Select tasks that need deadline pings.

    Returns list of (task, reason) tuples where reason is "tomorrow" or "overdue".
    Ignores tasks with status "done" and tasks without a deadline.
    """
    tomorrow = today + timedelta(days=1)
    result = []
    for t in tasks:
        if t.status == "done" or not t.deadline:
            continue
        try:
            d = _parse_date(t.deadline)
        except ValueError:
            # Кривая дата в таблице (например, после ручной правки) — пропускаем эту задачу,
            # не ломаем весь батч.
            continue
        if d < today:
            result.append((t, "overdue"))
        elif d == tomorrow:
            result.append((t, "tomorrow"))
    return result
