from datetime import date, datetime, timedelta

from task_bot.sheets import Task

STATUS_LABELS = {"todo": "🔵 todo", "in_progress": "🟡 в работе", "done": "🟢 готово"}


def filter_tasks(tasks, assignee=None, status=None) -> list[Task]:
    """Filter tasks by assignee and/or status."""
    result = tasks
    if assignee is not None:
        result = [t for t in result if t.assignee == assignee]
    if status is not None:
        result = [t for t in result if t.status == status]
    return result


def format_task_card(task: Task) -> str:
    """Format a single task as a detailed card with all fields."""
    lines = [
        f"#{task.id} {task.title}",
        f"Статус: {STATUS_LABELS.get(task.status, task.status)}",
        f"Исполнитель: {task.assignee}",
    ]
    if task.description:
        lines.append(f"Описание: {task.description}")
    if task.deadline:
        lines.append(f"Дедлайн: {task.deadline}")
    lines.append(f"Создал: {task.created_by} ({task.created_at})")
    if task.done_at:
        lines.append(f"Закрыта: {task.done_at}")
    return "\n".join(lines)


def format_task_list(tasks: list[Task]) -> str:
    """Format tasks as a compact list; show 'Нет задач' if empty."""
    if not tasks:
        return "Нет задач."
    return "\n".join(
        f"#{t.id} [{STATUS_LABELS.get(t.status, t.status)}] {t.title}"
        f"{' → ' + t.deadline if t.deadline else ''} ({t.assignee})"
        for t in tasks
    )


def _is_overdue(task: Task, today: date) -> bool:
    """Check if a task is overdue (has passed deadline and not done)."""
    if task.status == "done" or not task.deadline:
        return False
    try:
        return _parse_date(task.deadline) < today
    except ValueError:
        # Кривая дата в таблице — считаем задачу «не просроченной» и пропускаем.
        return False


def _parse_date(s: str) -> date:
    """Parse date string in format YYYY-MM-DD."""
    return datetime.strptime(s, "%Y-%m-%d").date()


def build_report(tasks: list[Task], today: date) -> str:
    """Build a structured report with three sections: in progress, overdue, and closed in last 7 days."""
    # Section 1: tasks currently in progress
    in_progress = [t for t in tasks if t.status == "in_progress"]

    # Section 2: tasks that are overdue (deadline passed but not done)
    overdue = [t for t in tasks if _is_overdue(t, today)]

    # Section 3: tasks closed in the last 7 days
    week_ago = today - timedelta(days=7)
    closed = []
    for t in tasks:
        if not (t.status == "done" and t.done_at):
            continue
        try:
            # done_at хранится как "YYYY-MM-DD HH:MM" — берём только дату.
            if _parse_date(t.done_at.split(" ")[0]) >= week_ago:
                closed.append(t)
        except ValueError:
            # Кривая дата done_at — пропускаем задачу, не ломаем отчёт.
            continue

    def block(title, items):
        """Format a report section with title and items."""
        if not items:
            return f"{title}: —"
        body = "\n".join(f"  #{t.id} {t.title} ({t.assignee})" for t in items)
        return f"{title}:\n{body}"

    return "\n\n".join([
        "📋 Сводка по задачам",
        block("🟡 В работе", in_progress),
        block("🔴 Просрочено", overdue),
        block("✅ Закрыто за 7 дней", closed),
    ])
