import logging
import re
from datetime import datetime, timedelta

import aiohttp
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

CHANNEL = "gid_lipetsk"
PREVIEW_URL = f"https://t.me/s/{CHANNEL}"

CATEGORY_KEYWORDS = {
    "concerts": ["концерт", "музык", "рок", "джаз", "поп", "группа", "певец", "певица", "live"],
    "art":      ["выставк", "экспозиц", "галере", "музей", "искусств", "художник"],
    "sport":    ["спорт", "футбол", "матч", "турнир", "бег", "тренировк", "соревнован"],
    "party":    ["вечеринк", "клуб", "дискотек", "party", "диджей", "dj"],
    "theater":  ["театр", "спектакл", "кино", "фильм", "премьер", "показ"],
    "quiz": ["квиз", "мозгобойн", "викторин", "игра", "quiz"],
}

MONTHS_RU = {
    "январ": 1, "феврал": 2, "март": 3, "апрел": 4,
    "мая": 5, "май": 5, "июн": 6, "июл": 7, "август": 8,
    "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12,
}


def detect_category(text: str) -> str:
    t = text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return cat
    return "other"


def extract_date(text: str):
    pattern = r"(\d{1,2})\s+(январ\w*|феврал\w*|март\w*|апрел\w*|ма[яй]\w*|июн\w*|июл\w*|август\w*|сентябр\w*|октябр\w*|ноябр\w*|декабр\w*)(?:\s+(\d{4}))?"
    m = re.search(pattern, text.lower())
    if m:
        day = int(m.group(1))
        month_word = m.group(2)
        year = int(m.group(3)) if m.group(3) else datetime.now().year
        for key, num in MONTHS_RU.items():
            if month_word.startswith(key):
                try:
                    return datetime(year, num, day), m.group(0)
                except Exception:
                    pass
    return None, ""


def extract_price(text: str) -> str:
    m = re.search(r"(бесплатн\w+|\d[\d\s]*[₽руб])", text.lower())
    return m.group(0).strip() if m else ""


class TelegramChannelParser:
    SOURCE = "@gid_lipetsk"

    def __init__(self, *args, **kwargs):
        pass  # Telethon больше не нужен

    async def get_events(self, category: str = None, days_ahead: int = 7) -> list:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(PREVIEW_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        log.warning(f"t.me/s/{CHANNEL} returned {resp.status}")
                        return []
                    html = await resp.text()
        except Exception as e:
            log.warning(f"TelegramChannelParser fetch error: {e}")
            return []

        soup = BeautifulSoup(html, "html.parser")
        messages = soup.select(".tgme_widget_message")
        events = []
        deadline = datetime.now() + timedelta(days=days_ahead)

        for msg in messages[-60:]:
            try:
                text_el = msg.select_one(".tgme_widget_message_text")
                if not text_el:
                    continue
                text = text_el.get_text(separator="\n").strip()
                if len(text) < 30:
                    continue

                detected_cat = detect_category(text)
                if category and detected_cat != category and detected_cat != "other":
                    continue

                date_obj, date_str = extract_date(text)
                if date_obj and date_obj > deadline:
                    continue

                pub_date_str = ""
                time_el = msg.select_one("time")
                if time_el and time_el.get("datetime"):
                    try:
                        pub_dt = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
                        pub_date_str = pub_dt.strftime("%d.%m.%Y")
                    except Exception:
                        pass

                lines = [l.strip() for l in text.split("\n") if l.strip()]
                title = lines[0][:100] if lines else text[:100]

                link_el = msg.select_one("a.tgme_widget_message_date")
                url = link_el["href"] if link_el and link_el.get("href") else f"https://t.me/{CHANNEL}"

                events.append({
                    "title": title,
                    "date": date_obj,
                    "date_str": date_str or pub_date_str,
                    "place": "",
                    "price": extract_price(text),
                    "url": url,
                    "category": detected_cat,
                    "source": self.SOURCE,
                })
            except Exception as e:
                log.debug(f"Post parse error: {e}")

        return events
