import html
import re
from datetime import date, datetime, timedelta

from task_bot.sheets import Task

# Ссылки в тексте — выделяем моноширинным (в Telegram тап по нему копирует)
_URL_RE = re.compile(r"(https?://\S+)")

# username -> отображаемое имя (заполняется при старте из конфига участников)
_DISPLAY_NAMES: dict[str, str] = {}


def set_display_names(mapping: dict[str, str]) -> None:
    """Запоминаем соответствие username -> имя (вызывается из main при старте)."""
    _DISPLAY_NAMES.update(mapping)


def name(username: str) -> str:
    """Имя для отображения вместо username (если задано в конфиге)."""
    return _DISPLAY_NAMES.get(username, username)

STATUS_LABELS = {"todo": "🔵 todo", "in_progress": "🟡 в работе", "done": "🟢 готово"}
# Без кружков — для компактного списка задач
STATUS_PLAIN = {"todo": "todo", "in_progress": "в работе", "done": "готово"}

_KEYCAPS = {str(d): f"{d}️⃣" for d in range(10)}


def kid(task_id) -> str:
    """Номер задачи как эмодзи-клавиши: 3 -> 3️⃣, 12 -> 1️⃣2️⃣."""
    return "".join(_KEYCAPS.get(c, c) for c in str(task_id))


def esc(text: str) -> str:
    """Экранируем пользовательский текст для HTML-разметки Telegram."""
    return html.escape(str(text))


def format_links(text: str) -> str:
    """Экранируем текст и заворачиваем ссылки в <code> — так их удобно копировать
    (в Telegram тап по моноширинному тексту копирует его целиком)."""
    parts = _URL_RE.split(str(text))
    out = []
    for i, part in enumerate(parts):
        # Нечётные части — это URL (split с группой их выделяет)
        out.append(f"<code>{esc(part)}</code>" if i % 2 else esc(part))
    return "".join(out)


_MONTHS_GEN = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def human_date(s: str) -> str:
    """Дату 'YYYY-MM-DD' переводим в человеческий вид '29 июня'.
    Если строка не распознана (пусто/кривой формат) — возвращаем как есть."""
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return esc(str(s))
    return f"{d.day} {_MONTHS_GEN[d.month]}"


def filter_tasks(tasks, assignee=None, status=None) -> list[Task]:
    """Filter tasks by assignee and/or status."""
    result = tasks
    if assignee is not None:
        result = [t for t in result if t.assignee == assignee]
    if status is not None:
        result = [t for t in result if t.status == status]
    return result


def format_task_card(task: Task) -> str:
    """Format a single task as a detailed card with all fields (HTML)."""
    lines = [
        f"{kid(task.id)} <b>{esc(task.title)}</b>",
        f"<b>Статус:</b> {STATUS_PLAIN.get(task.status, task.status)}",
        f"<b>Исполнитель:</b> {esc(name(task.assignee))}",
    ]
    if task.description:
        lines.append(f"<b>Описание:</b>\n{format_links(task.description)}")
    if task.deadline:
        lines.append(f"<b>Дедлайн:</b> {human_date(task.deadline)}")
    lines.append(f"<b>Создал:</b> {esc(name(task.created_by))} ({esc(task.created_at)})")
    if task.done_at:
        lines.append(f"<b>Закрыта:</b> {esc(task.done_at)}")
    return "\n".join(lines)


def format_task_list(tasks: list[Task]) -> str:
    """Format tasks as a compact list (HTML); show 'Нет задач' if empty."""
    if not tasks:
        return "Нет задач."
    return "\n".join(
        f"{kid(t.id)} {STATUS_PLAIN.get(t.status, t.status)} <b>{esc(t.title)}</b>"
        f"{' → ' + human_date(t.deadline) if t.deadline else ''} ({esc(name(t.assignee))})"
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
        body = "\n".join(f"  {kid(t.id)} {esc(t.title)} ({esc(name(t.assignee))})" for t in items)
        return f"<b>{title}:</b>\n{body}"

    return "\n\n".join([
        "📋 <b>Сводка по задачам</b>",
        block("🟡 В работе", in_progress),
        block("🔴 Просрочено", overdue),
        block("✅ Закрыто за 7 дней", closed),
    ])
