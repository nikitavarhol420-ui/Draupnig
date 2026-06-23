# Draupnir Task Bot — инструкция по запуску

Пошаговое руководство для запуска Telegram-бота управления задачами. Никакого опыта в программировании не нужно — просто следуй шагам.

---

## Шаг 1. Создать Telegram-бота через @BotFather

1. Открой Telegram и найди бота **@BotFather** (официальный, с синей галочкой).
2. Напиши ему `/newbot`.
3. BotFather спросит **название** бота — это то, что увидят люди в чате. Пример: `Draupnir Tasks`.
4. Затем спросит **username** — уникальный идентификатор, должен заканчиваться на `bot`. Пример: `draupnir_tasks_bot`.
5. BotFather пришлёт **токен** — длинную строку вида `123456789:AAF...`. Скопируй её, она понадобится в `.env`.

---

## Шаг 2. Создать Google Service Account и дать ему доступ к таблице

Бот читает и пишет в Google Sheets от имени «сервисного аккаунта» — это специальный технический e-mail от Google.

### 2.1 Создать проект в Google Cloud

1. Открой [console.cloud.google.com](https://console.cloud.google.com).
2. Вверху слева нажми на название проекта → **New Project** → дай любое имя → **Create**.

### 2.2 Включить Google Sheets API

1. В левом меню выбери **APIs & Services → Library**.
2. Найди **Google Sheets API** → нажми **Enable**.

### 2.3 Создать Service Account и скачать ключ

1. В меню выбери **APIs & Services → Credentials**.
2. Нажми **+ Create Credentials → Service account**.
3. Дай любое имя (например, `task-bot`) → **Create and Continue** → **Done**.
4. В списке Service Accounts нажми на созданный аккаунт.
5. Перейди на вкладку **Keys** → **Add Key → Create new key → JSON → Create**.
6. Браузер скачает файл `.json`. Переименуй его в `service_account.json` и положи в папку:
   ```
   /Users/nickvarhol/Work/Claude/Draupnir/task_bot/service_account.json
   ```

### 2.4 Расшарить таблицу на email service account (важно — без этого ничего не заработает)

1. Открой скачанный `service_account.json` любым текстовым редактором.
2. Найди поле `"client_email"` — там будет e-mail вида `task-bot@...iam.gserviceaccount.com`. Скопируй его.
3. Открой свою Google-таблицу.
4. Нажми кнопку **Поделиться** (Share) в правом верхнем углу.
5. Вставь этот e-mail, выбери роль **Редактор (Editor)** → **Готово**.

---

## Шаг 3. Узнать ID группового чата

Бот должен знать ID группы, чтобы отправлять туда еженедельные отчёты.

1. Добавь своего бота в группу (через кнопку **Add members** в настройках группы, введи username бота).
2. Добавь в эту же группу бота **@RawDataBot** (или **@getidsbot**).
3. Напиши любое сообщение в группе — @RawDataBot пришлёт ответ с данными чата. Найди поле `"id"` — это отрицательное число вида `-1001234567890`. Скопируй его.
4. После того как узнал ID — можешь удалить @RawDataBot из группы.

---

## Шаг 4. Заполнить файл `.env`

1. В папке `task_bot/` уже есть файл `.env.example` — скопируй его в `.env`:
   ```bash
   cp /Users/nickvarhol/Work/Claude/Draupnir/task_bot/.env.example \
      /Users/nickvarhol/Work/Claude/Draupnir/task_bot/.env
   ```
2. Открой `.env` и заполни каждую строку:

   ```dotenv
   # Токен от BotFather (шаг 1)
   BOT_TOKEN=123456789:AAF...

   # ID твоей Google-таблицы — это часть URL между /d/ и /edit
   # Пример URL: https://docs.google.com/spreadsheets/d/1AbCdEf.../edit
   SPREADSHEET_ID=1AbCdEf...

   # ID группового чата (шаг 3) — отрицательное число
   GROUP_CHAT_ID=-1001234567890

   # Путь к JSON-ключу service account (шаг 2.3)
   GOOGLE_CREDENTIALS=task_bot/service_account.json

   # Участники: username_без_собачки:Отображаемое_имя через запятую
   PARTICIPANTS=nick:Ник,alex:Алекс,maria:Мария

   # Время ежедневной проверки дедлайнов (HH:MM, 24-часовой формат)
   DAILY_CHECK_TIME=09:00

   # Время еженедельной сводки (каждый понедельник в это время)
   WEEKLY_REPORT_TIME=09:00
   ```

---

## Шаг 5. Запустить бота

Открой терминал и выполни:

```bash
cd /Users/nickvarhol/Work/Claude/Draupnir && .venv/bin/python3.14 -m task_bot.main
```

Если всё настроено правильно, увидишь:
```
Бот запущен. Ctrl+C для остановки.
```

Для остановки — нажми **Ctrl+C** в терминале.

---

## Шаг 6. Первый запуск — каждый участник делает /start

Чтобы бот мог слать **личные уведомления**, каждый участник из списка `PARTICIPANTS` должен:

1. Найти бота в Telegram по его username (например, `@draupnir_tasks_bot`).
2. Нажать **Start** или написать `/start` в личку боту.

Без этого шага уведомления о назначении задач и дедлайны до людей не дойдут — бот не знает их Telegram ID.

---

## Структура таблицы

Бот сам создаёт нужные листы при первом запуске:
- **Tasks** — все задачи с колонками: id, title, description, assignee, status, deadline, created_at, created_by, done_at.
- **Users** — участники, сделавшие /start: username, chat_id, display_name.

Ручная правка таблицы допустима — бот читает актуальные данные при каждом запросе.

---

## Команды бота

| Команда | Что делает |
|---------|------------|
| `/start` | Зарегистрироваться для личных уведомлений |
| `/new` | Создать новую задачу (пошаговый диалог) |
| `/tasks` | Список задач с фильтрами (мои / все / по статусу) |
| `/task N` | Карточка задачи N: сменить статус, переназначить |
| `/report` | Сводка по задачам прямо сейчас |
| `/help` | Справка по командам |

---

## Запуск на сервере (systemd)

После приёмки на локальной машине бот можно настроить на автономный запуск на сервере с автоматической переза грузкой при отказах.

### Подготовка

1. **Отредактируй файл** `task_bot/deploy/task-bot.service`:
   - Замени `REPLACE_USER` на реального пользователя сервера (например, `bot` или `ubuntu`).
   - Замени `/path/to/Draupnir` на полный путь к директории на сервере (например, `/home/bot/Draupnir`).

   Пример строки после редактирования:
   ```ini
   User=bot
   WorkingDirectory=/home/bot/Draupnir
   ExecStart=/home/bot/Draupnir/.venv/bin/python3.14 -m task_bot.main
   ```

### Установка

Выполни эти команды от пользователя с `sudo` прав:

```bash
# Скопировать файл сервиса в системную директорию
sudo cp task_bot/deploy/task-bot.service /etc/systemd/system/

# Перезагрузить systemd для регистрации нового сервиса
sudo systemctl daemon-reload

# Включить автозапуск и сразу запустить бота
sudo systemctl enable --now task-bot

# Проверить статус (должен быть active (running))
systemctl status task-bot

# Смотреть живые логи (Ctrl+C для выхода)
journalctl -u task-bot -f
```

### Проверка автономности

- **`systemctl status task-bot`** должна показать `active (running)`.
- После перезагрузки сервера (`sudo reboot`) бот автоматически поднимется.
- Если процесс упадёт, systemd перезапустит его через ~5 секунд.
- Проверь в Telegram, что бот отвечает на `/help`.

### Часовой пояс сервера (важно)

Переменные `DAILY_CHECK_TIME` и `WEEKLY_REPORT_TIME` в `.env`, а также метки времени `done_at` у задач опираются на **системный часовой пояс сервера**. Если сервер живёт в UTC, а ты ожидаешь отчёт в 09:00 по Москве — он придёт в 12:00 UTC, то есть в полдень по Москве.

Перед запуском убедись, что часовой пояс сервера совпадает с ожидаемым:

```bash
# Проверить текущий часовой пояс
timedatectl

# Установить нужный (пример для Москвы)
sudo timedatectl set-timezone Europe/Moscow
```
