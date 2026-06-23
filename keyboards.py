from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from task_bot.config import Participant


def _kb(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)


def assignee_keyboard(participants: list[Participant]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=p.display_name,
                                  callback_data=f"assignee:{p.username}")]
            for p in participants]
    return _kb(rows)


def description_keyboard() -> InlineKeyboardMarkup:
    return _kb([[InlineKeyboardButton(text="Пропустить",
                                      callback_data="desc:skip")]])


def deadline_keyboard() -> InlineKeyboardMarkup:
    return _kb([[InlineKeyboardButton(text="Без дедлайна",
                                      callback_data="deadline:none")]])


def status_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return _kb([
        [InlineKeyboardButton(text="🔵 todo", callback_data=f"status:{task_id}:todo"),
         InlineKeyboardButton(text="🟡 в работе", callback_data=f"status:{task_id}:in_progress"),
         InlineKeyboardButton(text="🟢 готово", callback_data=f"status:{task_id}:done")],
        [InlineKeyboardButton(text="↻ Переназначить", callback_data=f"reassign:{task_id}")],
    ])


def reassign_keyboard(task_id: int, participants) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=p.display_name,
                                  callback_data=f"setassignee:{task_id}:{p.username}")]
            for p in participants]
    return _kb(rows)


def tasks_filter_keyboard() -> InlineKeyboardMarkup:
    return _kb([
        [InlineKeyboardButton(text="Мои", callback_data="filter:mine"),
         InlineKeyboardButton(text="Все", callback_data="filter:all")],
        [InlineKeyboardButton(text="todo", callback_data="filter:todo"),
         InlineKeyboardButton(text="в работе", callback_data="filter:in_progress"),
         InlineKeyboardButton(text="готово", callback_data="filter:done")],
    ])
