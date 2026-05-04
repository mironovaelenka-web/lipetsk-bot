import asyncio
import logging
from datetime import datetime, timedelta

import aiohttp
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

BASE_URL = "https://lip.afishagoroda.ru"

CATEGORY_URLS = {
    "concerts": "/concerts",
    "art":      "/exhibitions",
    "sport":    "/sport",
    "party":    "/parties",
    "theater":  "/theaters",
    "festival": "/festivals",
}

MONTHS_RU = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}


def parse_date(text: str):
    """Парсит русскую дату вида '3 мая' или '3 мая 2025'."""
    try:
        parts = text.strip().lower().split()
        day = int(parts[0])
        month = MONTHS_RU.get(parts[1], 0)
        year = int(parts[2]) if len(parts) > 2 else datetime.now().year
        return datetime(year, month, day)
    except Exception:
        return None


class AfishaParser:
    SOURCE = "afishagoroda.ru"

    async def get_events(self, category: str = None, days_ahead: int = 7) -> list:
        categories = [category] if category and category in CATEGORY_URLS else list(CATEGORY_URLS.keys())
        results = []
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
            tasks = [self._parse_category(session, cat, days_ahead) for cat in categories]
            for coro in asyncio.as_completed(tasks):
                try:
                    events = await coro
                    results.extend(events)
                except Exception as e:
                    log.warning(f"AfishaParser category error: {e}")
        return results

    async def _parse_category(self, session: aiohttp.ClientSession, category: str, days_ahead: int) -> list:
        url = BASE_URL + CATEGORY_URLS[category]
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        except Exception as e:
            log.warning(f"AfishaParser fetch error {url}: {e}")
            return []

        soup = BeautifulSoup(html, "html.parser")
        events = []
        deadline = datetime.now() + timedelta(days=days_ahead)

        # Ищем карточки мероприятий (структура afishagoroda.ru)
        cards = soup.select(".event-item, .afisha-item, .poster-item, article.event")
        if not cards:
            # Запасной селектор
            cards = soup.select("a[href*='/event/'], a[href*='/afisha/']")

        for card in cards[:20]:
            try:
                title_el = card.select_one("h2, h3, .title, .name, .event-title")
                title = title_el.get_text(strip=True) if title_el else card.get_text(strip=True)[:80]
                if not title:
                    continue

                date_el = card.select_one(".date, .event-date, time, .when")
                date_str = date_el.get_text(strip=True) if date_el else ""
                date_obj = parse_date(date_str) if date_str else None

                if date_obj and date_obj > deadline:
                    continue

                place_el = card.select_one(".place, .venue, .location, .where")
                place = place_el.get_text(strip=True) if place_el else ""

                price_el = card.select_one(".price, .cost, .ticket-price")
                price = price_el.get_text(strip=True) if price_el else ""

                link = card.get("href") or (card.select_one("a") or {}).get("href", "")
                if link and not link.startswith("http"):
                    link = BASE_URL + link

                events.append({
                    "title": title,
                    "date": date_obj,
                    "date_str": date_str,
                    "place": place,
                    "price": price,
                    "url": link,
                    "category": category,
                    "source": self.SOURCE,
                })
            except Exception as e:
                log.debug(f"Card parse error: {e}")

        return events
