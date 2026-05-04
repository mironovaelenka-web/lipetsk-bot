"""
Запусти этот скрипт ОДИН РАЗ локально на компьютере,
чтобы получить строку сессии Telethon для переменной TELETHON_SESSION.

Установи зависимости:
    pip install telethon

Запуск:
    python generate_session.py
"""

import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(input("Введи api_id (с my.telegram.org): "))
API_HASH = input("Введи api_hash: ").strip()


async def main():
    async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        session_str = client.session.save()
        print("\n" + "=" * 60)
        print("✅ Твоя строка сессии (скопируй в TELETHON_SESSION на Render):")
        print("=" * 60)
        print(session_str)
        print("=" * 60)


asyncio.run(main())
