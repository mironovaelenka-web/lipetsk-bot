import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import Database
from sources.afisha import AfishaParser
from sources.timepad import TimepadParser
from sources.telegram_channel import TelegramChannelParser

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
TG_CHANNEL = os.environ.get("TG_CHANNEL", "gid_lipetsk")

CATEGORIES = {
    "concerts": "🎵 Концерты",
    "art": "🖼 Выставки",
    "sport": "🏃 Спорт",
    "party": "🎉 Вечеринки",
    "theater": "🎭 Театр и кино",
    "festival": "🎪 Фестивали",
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def fetch_all_events(category=None, days_ahead=3):
    results = []
    parsers = [
        AfishaParser(),
        TimepadParser(),
        TelegramChannelParser(),
    ]
    for parser in parsers:
        try:
            events = await parser.get_events(category=category, days_ahead=days_ahead)
            results.extend(events)
        except Exception as e:
            log.warning(f"{parser.__class__.__name__} error: {e}")
    results.sort(key=lambda x: x.get("date") or datetime.max)
    return results


def format_event(event):
    icons = {"concerts": "🎵", "art": "🖼", "sport": "🏃", "party": "🎉", "theater": "🎭", "festival": "🎪"}
    icon = icons.get(event.get("category", ""), "📌")
    lines = [f"{icon} <b>{event['title']}</b>"]
    if event.get("date_str"):
        lines.append(f"📅 {event['date_str']}")
    if event.get("place"):
        lines.append(f"📍 {event['place']}")
    if event.get("price"):
        lines.append(f"💰 {event['price']}")
    if event.get("url"):
        lines.append(f"🔗 <a href='{event['url']}'>Подробнее</a>")
    if event.get("source"):
        lines.append(f"<i>{event['source']}</i>")
    return "\n".join(lines)


def main_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Сегодня", callback_data="today")
    kb.button(text="🗓 На выходных", callback_data="weekend")
    kb.button(text="🔍 По категории", callback_data="categories")
    kb.button(text="⚙️ Настройки", callback_data="settings")
    kb.adjust(2)
    return kb.as_markup()


def categories_keyboard():
    kb = InlineKeyboardBuilder()
    for key, label in CATEGORIES.items():
        kb.button(text=label, callback_data=f"cat_{key}")
    kb.button(text="◀️ Назад", callback_data="back_main")
    kb.adjust(2)
    return kb.as_markup()


def settings_keyboard(user_id):
    prefs = db.get_prefs(user_id)
    notif_text = "🔔 Рассылка: вкл ✅" if prefs.get("notify", True) else "🔕 Рассылка: выкл ❌"
    kb = InlineKeyboardBuilder()
    kb.button(text=notif_text, callback_data="toggle_notify")
    kb.button(text=f"⏰ Время: {prefs.get('notify_time', '09:00')}", callback_data="noop")
    kb.button(text="◀️ Назад", callback_data="back_main")
    kb.adjust(1)
    return kb.as_markup()


async def send_events(chat_id, events, title):
    if not events:
        await bot.send_message(chat_id, f"{title}\n\n😔 Пока ничего не нашли.", parse_mode="HTML", reply_markup=main_keyboard())
        return
    await bot.send_message(chat_id, f"{title}\n\nНашёл <b>{len(events)}</b> мероприятий:", parse_mode="HTML")
    for ev in events[:10]:
        try:
            await bot.send_message(chat_id, format_event(ev), parse_mode="HTML", disable_web_page_preview=True)
            await asyncio.sleep(0.3)
        except Exception as e:
            log.warning(f"Send error: {e}")
    await bot.send_message(chat_id, "Что ещё ищем? 👇", reply_markup=main_keyboard())


@dp.message(Command("start"))
async def cmd_start(message: Message):
    db.add_user(message.from_user.id)
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я слежу за мероприятиями в <b>Липецке</b>.\n\n"
        "Источники: afishagoroda.ru · Timepad · @gid_lipetsk\n\n"
        "Что ищем? 👇",
        parse_mode="HTML",
        reply_markup=main_keyboard()
    )


@dp.message(Command("today"))
async def cmd_today(message: Message):
    await message.answer("🔍 Ищу на сегодня...")
    events = await fetch_all_events(days_ahead=1)
    await send_events(message.chat.id, events, "📅 <b>Сегодня в Липецке</b>")


@dp.message(Command("weekend"))
async def cmd_weekend(message: Message):
    await message.answer("🔍 Ищу на выходные...")
    events = await fetch_all_events(days_ahead=7)
    await send_events(message.chat.id, events, "🗓 <b>На выходных в Липецке</b>")


@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    prefs = db.get_prefs(message.from_user.id)
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        f"📍 Город: Липецк\n"
        f"🔔 Рассылка: {'включена' if prefs.get('notify', True) else 'выключена'}\n"
        f"⏰ Время: {prefs.get('notify_time', '09:00')}",
        parse_mode="HTML",
        reply_markup=settings_keyboard(message.from_user.id)
    )


@dp.message(F.text)
async def text_search(message: Message):
    text = message.text.lower()
    category_map = {
        ("концерт", "музык", "рок", "джаз"): "concerts",
        ("выставк", "искусств", "галере"): "art",
        ("спорт", "футбол", "бег"): "sport",
        ("вечеринк", "клуб", "дискотек"): "party",
        ("театр", "кино", "спектакл"): "theater",
        ("фестивал", "маркет", "ярмарк"): "festival",
    }
    category = None
    for keywords, cat in category_map.items():
        if any(kw in text for kw in keywords):
            category = cat
            break
    await message.answer("🔍 Ищу...")
    events = await fetch_all_events(category=category, days_ahead=7)
    title = f"{CATEGORIES[category]} <b>в Липецке</b>" if category else f"🔍 <b>Результаты</b>"
    await send_events(message.chat.id, events, title)


@dp.callback_query(F.data == "today")
async def cb_today(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer("🔍 Ищу на сегодня...")
    events = await fetch_all_events(days_ahead=1)
    await send_events(cb.message.chat.id, events, "📅 <b>Сегодня в Липецке</b>")


@dp.callback_query(F.data == "weekend")
async def cb_weekend(cb: CallbackQuery):
    await cb.answer()
    await cb.message.answer("🔍 Ищу на выходные...")
    events = await fetch_all_events(days_ahead=7)
    await send_events(cb.message.chat.id, events, "🗓 <b>На выходных в Липецке</b>")


@dp.callback_query(F.data == "categories")
async def cb_categories(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("Выбери категорию 👇", reply_markup=categories_keyboard())


@dp.callback_query(F.data.startswith("cat_"))
async def cb_category(cb: CallbackQuery):
    await cb.answer()
    cat = cb.data.replace("cat_", "")
    label = CATEGORIES.get(cat, "Мероприятия")
    await cb.message.answer(f"🔍 Ищу: {label}...")
    events = await fetch_all_events(category=cat, days_ahead=7)
    await send_events(cb.message.chat.id, events, f"{label} <b>в Липецке</b>")


@dp.callback_query(F.data == "settings")
async def cb_settings(cb: CallbackQuery):
    await cb.answer()
    prefs = db.get_prefs(cb.from_user.id)
    await cb.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        f"📍 Город: Липецк\n"
        f"🔔 Рассылка: {'включена' if prefs.get('notify', True) else 'выключена'}\n"
        f"⏰ Время: {prefs.get('notify_time', '09:00')}",
        parse_mode="HTML",
        reply_markup=settings_keyboard(cb.from_user.id)
    )


@dp.callback_query(F.data == "toggle_notify")
async def cb_toggle_notify(cb: CallbackQuery):
    prefs = db.get_prefs(cb.from_user.id)
    new_val = not prefs.get("notify", True)
    db.set_pref(cb.from_user.id, "notify", new_val)
    status = "включена ✅" if new_val else "выключена ❌"
    await cb.answer(f"Рассылка {status}", show_alert=True)
    await cb.message.edit_reply_markup(reply_markup=settings_keyboard(cb.from_user.id))


@dp.callback_query(F.data == "back_main")
async def cb_back_main(cb: CallbackQuery):
    await cb.answer()
    await cb.message.edit_text("Что ищем? 👇", reply_markup=main_keyboard())


@dp.callback_query(F.data == "noop")
async def cb_noop(cb: CallbackQuery):
    await cb.answer()


async def daily_broadcast():
    log.info("Daily broadcast...")
    users = db.get_subscribed_users()
    events = await fetch_all_events(days_ahead=1)
    today_str = datetime.now().strftime("%d.%m.%Y")
    title = f"🌅 <b>Доброе утро! Афиша Липецка на {today_str}</b>"
    for user_id in users:
        try:
            await send_events(user_id, events, title)
            await asyncio.sleep(0.5)
        except Exception as e:
            log.warning(f"Broadcast error {user_id}: {e}")


async def main():
    db.init()
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="today", description="Мероприятия сегодня"),
        BotCommand(command="weekend", description="На выходных"),
        BotCommand(command="settings", description="Настройки"),
    ])
    scheduler.add_job(daily_broadcast, "cron", hour=9, minute=0)
    scheduler.start()
    log.info("Bot is running.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
