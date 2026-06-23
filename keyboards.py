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
        [InlineKeyboardButton(text="todo", callback_data=f"status:{task_id}:todo"),
         InlineKeyboardButton(text="в работе", callback_data=f"status:{task_id}:in_progress"),
         InlineKeyboardButton(text="готово", callback_data=f"status:{task_id}:done")],
        [InlineKeyboardButton(text="Переназначить", callback_data=f"reassign:{task_id}")],
        [InlineKeyboardButton(text="Отменить задачу", callback_data=f"cancel:{task_id}")],
    ])


def confirm_delete_keyboard(task_id: int) -> InlineKeyboardMarkup:
    # Подтверждение необратимого удаления задачи
    return _kb([
        [InlineKeyboardButton(text="Да, удалить", callback_data=f"delyes:{task_id}"),
         InlineKeyboardButton(text="Нет", callback_data=f"delno:{task_id}")],
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
        [InlineKeyboardButton(text="По человеку", callback_data="filter:byperson")],
    ])


def person_filter_keyboard(participants: list[Participant]) -> InlineKeyboardMarkup:
    # Кнопки участников — показать задачи выбранного человека
    rows = [[InlineKeyboardButton(text=p.display_name,
                                  callback_data=f"byperson:{p.username}")]
            for p in participants]
    return _kb(rows)
