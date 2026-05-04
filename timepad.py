import logging
from datetime import datetime, timedelta

import aiohttp

log = logging.getLogger(__name__)

API_URL = "https://api.timepad.ru/v1/events"

CATEGORY_IDS = {
    "concerts": [362, 363, 364],   # музыка, концерты
    "art":      [371, 372],        # выставки, искусство
    "sport":    [375, 376],        # спорт
    "party":    [380],             # вечеринки
    "theater":  [366, 367],        # театр, кино
    "festival": [368, 369],        # фестивали, маркеты
}


class TimepadParser:
    SOURCE = "Timepad"

    async def get_events(self, category: str = None, days_ahead: int = 7) -> list:
        now = datetime.now()
        date_from = now.strftime("%Y-%m-%dT%H:%M:%S")
        date_to = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%dT%H:%M:%S")

        params = {
            "city": "Липецк",
            "starts_at_min": date_from,
            "starts_at_max": date_to,
            "limit": 50,
            "sort": "+starts_at",
            "fields": "id,name,starts_at,ends_at,location,ticket_types,url,organization",
            "access_status": "public",
        }

        if category and category in CATEGORY_IDS:
            params["category_ids"] = ",".join(str(i) for i in CATEGORY_IDS[category])

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    API_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        log.warning(f"Timepad API status: {resp.status}")
                        return []
                    data = await resp.json()
        except Exception as e:
            log.warning(f"Timepad fetch error: {e}")
            return []

        events = []
        for item in data.get("values", []):
            try:
                title = item.get("name", "").strip()
                if not title:
                    continue

                starts_at = item.get("starts_at", "")
                date_obj = None
                date_str = ""
                if starts_at:
                    try:
                        date_obj = datetime.fromisoformat(starts_at[:19])
                        date_str = date_obj.strftime("%d.%m.%Y %H:%M")
                    except Exception:
                        date_str = starts_at[:16]

                location = item.get("location", {})
                place = location.get("address", "") or location.get("city", "Липецк")

                # Цена из ticket_types
                tickets = item.get("ticket_types", [])
                price = ""
                if tickets:
                    prices = [t.get("price", 0) for t in tickets if t.get("price") is not None]
                    if prices:
                        min_price = min(prices)
                        price = "бесплатно" if min_price == 0 else f"от {min_price} ₽"

                url = item.get("url", "")

                events.append({
                    "title": title,
                    "date": date_obj,
                    "date_str": date_str,
                    "place": place,
                    "price": price,
                    "url": url,
                    "category": category or "other",
                    "source": self.SOURCE,
                })
            except Exception as e:
                log.debug(f"Timepad item parse error: {e}")

        return events
