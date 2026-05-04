# 🎯 CityEvents Bot — Афиша Липецка

Telegram-бот для мониторинга мероприятий в Липецке.  
Источники: afishagoroda.ru, Timepad, канал @gid_lipetsk.

---

## 🚀 Деплой на Render (бесплатно, шаг за шагом)

### Шаг 1 — Получи токен бота

1. Открой Telegram, найди **@BotFather**
2. Напиши `/newbot`
3. Придумай имя и username (например `lipetsk_events_bot`)
4. Скопируй **токен** — он выглядит так: `7123456789:AAF...`

---

### Шаг 2 — Получи Telegram API ключи (для чтения @gid_lipetsk)

1. Зайди на **https://my.telegram.org**
2. Войди в свой аккаунт Telegram
3. Нажми **API development tools**
4. Заполни форму (название приложения — любое, например `LipetskBot`)
5. Скопируй `api_id` (число) и `api_hash` (строка)

---

### Шаг 3 — Сгенерируй строку сессии Telethon

Это нужно сделать **один раз** на своём компьютере:

```bash
pip install telethon
python generate_session.py
```

Введи api_id и api_hash — скрипт выведет строку сессии.  
Скопируй её — она понадобится на шаге 5.

---

### Шаг 4 — Загрузи код на GitHub

1. Зарегистрируйся на **github.com** (если нет аккаунта)
2. Создай новый репозиторий: **New repository** → назови `lipetsk-bot` → Create
3. Загрузи все файлы этой папки в репозиторий:
   - Можно через кнопку **"uploading an existing file"** на GitHub
   - Или через Git если умеешь

---

### Шаг 5 — Задеплой на Render

1. Зайди на **render.com** → Sign Up (через GitHub)
2. Нажми **New** → **Web Service** (или **Background Worker**)
3. Выбери свой репозиторий `lipetsk-bot`
4. Настройки:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
5. Перейди в раздел **Environment** и добавь переменные:

| Переменная | Значение |
|---|---|
| `BOT_TOKEN` | токен от @BotFather |
| `TELETHON_API_ID` | число из my.telegram.org |
| `TELETHON_API_HASH` | строка из my.telegram.org |
| `TELETHON_SESSION` | строка из generate_session.py |
| `TG_CHANNEL` | `gid_lipetsk` |

6. Нажми **Deploy** — готово! 🎉

---

## 📁 Структура проекта

```
lipetsk_bot/
├── bot.py                  # Основной файл бота
├── database.py             # База данных (SQLite)
├── requirements.txt        # Зависимости Python
├── render.yaml             # Конфиг для Render
├── generate_session.py     # Генерация Telethon сессии
└── sources/
    ├── afisha.py           # Парсер afishagoroda.ru
    ├── timepad.py          # Timepad API
    └── telegram_channel.py # Чтение канала @gid_lipetsk
```

---

## 💬 Команды бота

| Команда | Что делает |
|---|---|
| `/start` | Главное меню |
| `/today` | Мероприятия на сегодня |
| `/weekend` | На выходных |
| `/settings` | Настройки рассылки |
| `/help` | Помощь |

Также бот понимает текст: напиши **концерты**, **выставки**, **спорт** и т.д.

---

## ⏰ Ежедневная рассылка

Бот автоматически отправляет подборку мероприятий **каждый день в 09:00** по московскому времени.  
Рассылку можно отключить в настройках (`/settings`).
