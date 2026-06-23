from datetime import datetime
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, FSInputFile

# Лицо «когда всё готово» лежит в папке task_bot/ (на уровень выше handlers/)
_DONE_FACE = str(Path(__file__).parent.parent / "когда все сделано.png")

from task_bot.config import Config
from task_bot.sheets import SheetsStore
from task_bot import keyboards as kb
from task_bot.reporting import filter_tasks, format_task_card, format_task_list, kid, esc


class NewTask(StatesGroup):
    title = State()
    description = State()
    assignee = State()
    deadline = State()


def build_tasks_router(config: Config, store: SheetsStore, notifier) -> Router:
    router = Router()

    # ---------- /new (пошаговый FSM-диалог) ----------

    @router.message(Command("new"))
    async def new_start(message: Message, state: FSMContext):
        # Inline correction #1: сохраняем создателя сразу на первом шаге,
        # пока message.from_user доступен напрямую (не через callback).
        await state.update_data(
            creator=message.from_user.username or str(message.from_user.id)
        )
        await state.set_state(NewTask.title)
        await message.answer("Заголовок задачи?")

    @router.message(NewTask.title)
    async def new_title(message: Message, state: FSMContext):
        await state.update_data(title=message.text)
        await state.set_state(NewTask.description)
        await message.answer(
            "Описание? (или Пропустить)",
            reply_markup=kb.description_keyboard(),
        )

    @router.message(NewTask.description)
    async def new_description(message: Message, state: FSMContext):
        await state.update_data(description=message.text)
        await _ask_assignee(message, state)

    @router.callback_query(NewTask.description, F.data == "desc:skip")
    async def new_description_skip(cb: CallbackQuery, state: FSMContext):
        await state.update_data(description="")
        await _ask_assignee(cb.message, state)
        await cb.answer()

    # Общий шаг: предложить выбрать исполнителя (используется и из /new, и из /task reply)
    async def _ask_assignee(message: Message, state: FSMContext):
        await state.set_state(NewTask.assignee)
        await message.answer(
            "Кому назначить?",
            reply_markup=kb.assignee_keyboard(config.participants),
        )

    @router.callback_query(NewTask.assignee, F.data.startswith("assignee:"))
    async def new_assignee(cb: CallbackQuery, state: FSMContext):
        username = cb.data.split(":", 1)[1]
        await state.update_data(assignee=username)
        await state.set_state(NewTask.deadline)
        await cb.message.answer(
            "Дедлайн в формате ГГГГ-ММ-ДД? (или Без дедлайна)",
            reply_markup=kb.deadline_keyboard(),
        )
        await cb.answer()

    @router.callback_query(NewTask.deadline, F.data == "deadline:none")
    async def new_deadline_none(cb: CallbackQuery, state: FSMContext):
        await _finish(cb.message, state, "")
        await cb.answer()

    @router.message(NewTask.deadline)
    async def new_deadline(message: Message, state: FSMContext):
        text = message.text.strip()
        try:
            datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            await message.answer("Не похоже на дату ГГГГ-ММ-ДД. Повтори.")
            return
        await _finish(message, state, text)

    # Финальный шаг FSM: создать задачу в хранилище и уведомить исполнителя.
    async def _finish(message: Message, state: FSMContext, deadline: str):
        data = await state.get_data()

        # Защита от протухшего FSM-состояния после перезапуска бота:
        # inline-кнопка могла сработать уже когда state пустой → KeyError.
        if not data.get("title") or not data.get("assignee"):
            await message.answer("Сессия устарела — начни заново через /new.")
            await state.clear()
            return

        # Inline correction #2: берём creator из FSM-данных, а не из message.chat.username.
        # message здесь может быть cb.message (объект из callback), где chat — групповой чат,
        # а не пользователь, поэтому username будет None. Creator сохранён на шаге new_start
        # или в reply-ветке task_command.
        creator = data.get("creator", str(message.chat.id))
        task = store.add_task(
            title=data["title"],
            description=data.get("description", ""),
            assignee=data["assignee"],
            deadline=deadline,
            created_by=creator,
        )
        await state.clear()
        await message.answer(
            "Задача создана:\n\n" + format_task_card(task),
            reply_markup=kb.status_keyboard(task.id),
        )
        await notifier(task)

    # ---------- /tasks (список с кнопками фильтра) ----------

    @router.message(Command("tasks"))
    async def tasks_list(message: Message):
        tasks = store.list_tasks()
        await message.answer(
            format_task_list(tasks),
            reply_markup=kb.tasks_filter_keyboard(),
        )

    @router.callback_query(F.data.startswith("filter:"))
    async def tasks_filter(cb: CallbackQuery):
        kind = cb.data.split(":", 1)[1]
        # "По человеку" — показываем кнопки участников, список придёт следующим шагом
        if kind == "byperson":
            await cb.message.answer(
                "Чьи задачи показать?",
                reply_markup=kb.person_filter_keyboard(config.participants),
            )
            await cb.answer()
            return
        tasks = store.list_tasks()
        if kind == "mine":
            username = cb.from_user.username or str(cb.from_user.id)
            tasks = filter_tasks(tasks, assignee=username)
        elif kind in ("todo", "in_progress", "done"):
            tasks = filter_tasks(tasks, status=kind)
        # "all" — задачи уже не фильтруем
        await cb.message.answer(format_task_list(tasks))
        await cb.answer()

    @router.callback_query(F.data.startswith("byperson:"))
    async def tasks_by_person(cb: CallbackQuery):
        # callback_data: "byperson:{username}" — список задач выбранного человека
        username = cb.data.split(":", 1)[1]
        tasks = filter_tasks(store.list_tasks(), assignee=username)
        await cb.message.answer(f"Задачи @{esc(username)}:\n\n" + format_task_list(tasks))
        await cb.answer()

    # ---------- /task : три ветки ----------

    @router.message(Command("task"))
    async def task_command(message: Message, state: FSMContext):
        # Ветка 1: reply на сообщение → создаём задачу из его текста (FSM).
        # Проверяем первой, до разбора аргументов.
        if message.reply_to_message and message.reply_to_message.text:
            title = message.reply_to_message.text
            await state.update_data(
                title=title,
                description="",
                # Сохраняем creator здесь, чтобы _finish мог его прочитать.
                creator=message.from_user.username or str(message.from_user.id),
            )
            await _ask_assignee(message, state)
            return

        # Ветка 2: /task N → показать карточку задачи N.
        parts = message.text.split()
        if len(parts) >= 2 and parts[1].isdigit():
            task = store.get_task(int(parts[1]))
            if task is None:
                await message.answer("Задача не найдена.")
                return
            await message.answer(
                format_task_card(task),
                reply_markup=kb.status_keyboard(task.id),
            )
            return

        # Ветка 3: ни reply, ни номер → подсказка по использованию.
        await message.answer(
            "Использование:\n"
            "• Ответь (reply) на сообщение и напиши /task — создать задачу из него\n"
            "• /task N — показать карточку задачи N"
        )

    # ---------- Смена статуса ----------

    @router.callback_query(F.data.startswith("status:"))
    async def change_status(cb: CallbackQuery):
        # callback_data: "status:{id}:{status}"
        _, task_id, status = cb.data.split(":", 2)
        task = store.set_status(int(task_id), status)
        if task is None:
            await cb.answer("Задача не найдена", show_alert=True)
            return
        await cb.message.edit_text(
            format_task_card(task),
            reply_markup=kb.status_keyboard(task.id),
        )
        await cb.answer("Статус обновлён")
        # Задачу закрыли — шлём лицо «когда всё готово» с поздравлением
        if status == "done":
            caption = (
                "YESS YEEESSSS YEEEAH\n\n"
                f"{kid(task.id)} {esc(task.title)}\n"
                "Готово"
            )
            await cb.message.answer_photo(FSInputFile(_DONE_FACE), caption=caption)

    # ---------- Переназначение ----------

    @router.callback_query(F.data.startswith("reassign:"))
    async def reassign_start(cb: CallbackQuery):
        # callback_data: "reassign:{id}"
        task_id = int(cb.data.split(":", 1)[1])
        await cb.message.answer(
            "На кого переназначить?",
            reply_markup=kb.reassign_keyboard(task_id, config.participants),
        )
        await cb.answer()

    @router.callback_query(F.data.startswith("setassignee:"))
    async def reassign_set(cb: CallbackQuery):
        # callback_data: "setassignee:{id}:{username}"
        _, task_id, username = cb.data.split(":", 2)
        task = store.set_assignee(int(task_id), username)
        if task is None:
            await cb.answer("Задача не найдена", show_alert=True)
            return
        await cb.message.answer("Переназначено:\n\n" + format_task_card(task))
        await cb.answer()
        await notifier(task)

    # ---------- Отмена (удаление) задачи ----------

    @router.callback_query(F.data.startswith("cancel:"))
    async def cancel_ask(cb: CallbackQuery):
        # callback_data: "cancel:{id}" — спрашиваем подтверждение, т.к. удаление необратимо
        task_id = int(cb.data.split(":", 1)[1])
        task = store.get_task(task_id)
        if task is None:
            await cb.answer("Задача не найдена", show_alert=True)
            return
        await cb.message.answer(
            f"Точно удалить задачу {kid(task.id)} {esc(task.title)}? Это необратимо.",
            reply_markup=kb.confirm_delete_keyboard(task_id),
        )
        await cb.answer()

    @router.callback_query(F.data.startswith("delyes:"))
    async def cancel_confirm(cb: CallbackQuery):
        # callback_data: "delyes:{id}" — подтверждено, удаляем строку
        task_id = int(cb.data.split(":", 1)[1])
        ok = store.delete_task(task_id)
        if not ok:
            await cb.answer("Задача не найдена", show_alert=True)
            return
        await cb.message.edit_text(f"Задача {kid(task_id)} удалена.")
        await cb.answer("Удалено")

    @router.callback_query(F.data.startswith("delno:"))
    async def cancel_abort(cb: CallbackQuery):
        # callback_data: "delno:{id}" — передумали
        await cb.message.edit_text("Удаление отменено, задача на месте.")
        await cb.answer()

    return router
