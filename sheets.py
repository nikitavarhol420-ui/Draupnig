from dataclasses import dataclass
from datetime import datetime

import gspread


# Порядок колонок в листе Tasks — менять нельзя без миграции данных
TASK_HEADERS = [
    "id", "title", "description", "assignee", "status",
    "deadline", "created_at", "created_by", "done_at",
]
# Порядок колонок в листе Users
USER_HEADERS = ["username", "chat_id", "display_name"]


@dataclass
class Task:
    id: int
    title: str
    description: str
    assignee: str
    status: str
    deadline: str
    created_at: str
    created_by: str
    done_at: str


def task_to_row(task: Task) -> list[str]:
    # Порядок строго как в TASK_HEADERS; всё приводим к строке для Sheets
    return [str(getattr(task, name)) for name in TASK_HEADERS]


def row_to_task(row: list[str]) -> Task:
    # Sheets отдаёт строки; дополняем недостающие ячейки пустыми
    padded = list(row) + [""] * (len(TASK_HEADERS) - len(row))
    data = dict(zip(TASK_HEADERS, padded))
    return Task(
        id=int(data["id"]),
        title=data["title"],
        description=data["description"],
        assignee=data["assignee"],
        status=data["status"],
        deadline=data["deadline"],
        created_at=data["created_at"],
        created_by=data["created_by"],
        done_at=data["done_at"],
    )


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


class SheetsStore:
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        gc = gspread.service_account(filename=credentials_path)
        sh = gc.open_by_key(spreadsheet_id)
        self._tasks_ws = self._ensure_ws(sh, "Tasks", TASK_HEADERS)
        self._users_ws = self._ensure_ws(sh, "Users", USER_HEADERS)

    def _ensure_ws(self, sh, title: str, headers: list[str]):
        # Берём лист или создаём с заголовком, если его нет
        try:
            ws = sh.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=title, rows=100, cols=len(headers))
            ws.append_row(headers)
        if ws.row_values(1) != headers:
            ws.update("A1", [headers])
        return ws

    def _all_task_rows(self) -> list[list[str]]:
        # Все строки кроме заголовка
        return self._tasks_ws.get_all_values()[1:]

    def list_tasks(self) -> list[Task]:
        return [row_to_task(r) for r in self._all_task_rows() if r and r[0]]

    def _next_id(self) -> int:
        tasks = self.list_tasks()
        return max((t.id for t in tasks), default=0) + 1

    def get_task(self, task_id: int) -> "Task | None":
        for t in self.list_tasks():
            if t.id == task_id:
                return t
        return None

    def _row_index(self, task_id: int) -> "int | None":
        # Номер строки в листе (1-based, с учётом заголовка)
        for idx, r in enumerate(self._all_task_rows(), start=2):
            if r and r[0] and int(r[0]) == task_id:
                return idx
        return None

    def add_task(self, title, description, assignee, deadline, created_by) -> Task:
        task = Task(
            id=self._next_id(), title=title, description=description,
            assignee=assignee, status="todo", deadline=deadline,
            created_at=_now_str(), created_by=created_by, done_at="",
        )
        self._tasks_ws.append_row(task_to_row(task))
        return task

    def set_status(self, task_id, status) -> "Task | None":
        idx = self._row_index(task_id)
        if idx is None:
            return None
        task = row_to_task(self._tasks_ws.row_values(idx))
        task.status = status
        task.done_at = _now_str() if status == "done" else ""
        self._tasks_ws.update(f"A{idx}", [task_to_row(task)])
        return task

    def set_assignee(self, task_id, assignee) -> "Task | None":
        idx = self._row_index(task_id)
        if idx is None:
            return None
        task = row_to_task(self._tasks_ws.row_values(idx))
        task.assignee = assignee
        self._tasks_ws.update(f"A{idx}", [task_to_row(task)])
        return task

    def delete_task(self, task_id) -> bool:
        # Физически удаляет строку задачи из листа. Необратимо.
        idx = self._row_index(task_id)
        if idx is None:
            return False
        self._tasks_ws.delete_rows(idx)
        return True

    def get_user_chat_id(self, username: str) -> "int | None":
        for r in self._users_ws.get_all_values()[1:]:
            if r and r[0] == username and len(r) > 1 and r[1]:
                return int(r[1])
        return None

    def upsert_user(self, username, chat_id, display_name) -> None:
        rows = self._users_ws.get_all_values()[1:]
        for idx, r in enumerate(rows, start=2):
            if r and r[0] == username:
                self._users_ws.update(
                    f"A{idx}", [[username, str(chat_id), display_name]]
                )
                return
        self._users_ws.append_row([username, str(chat_id), display_name])
