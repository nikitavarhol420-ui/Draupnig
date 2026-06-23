from task_bot.sheets import Task, task_to_row, row_to_task, TASK_HEADERS


def make_task():
    return Task(
        id=1, title="Допилить ноутбук", description="PCA по tech-сектору",
        assignee="nick", status="todo", deadline="2026-07-01",
        created_at="2026-06-23 10:00", created_by="alex", done_at="",
    )


def test_task_to_row_matches_headers_length():
    row = task_to_row(make_task())
    assert len(row) == len(TASK_HEADERS)


def test_row_to_task_is_inverse_of_task_to_row():
    task = make_task()
    assert row_to_task(task_to_row(task)) == task


def test_row_to_task_handles_string_id():
    # Google Sheets всё отдаёт строками — id должен стать int
    task = make_task()
    row = task_to_row(task)
    assert isinstance(row_to_task(row).id, int)
