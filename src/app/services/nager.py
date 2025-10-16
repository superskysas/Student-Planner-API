from __future__ import annotations

import re
from typing import Any, Dict, List

import httpx

NAGER_BASE_URL = "https://date.nager.at/api/v3/PublicHolidays"


async def fetch_nager_public_holidays(year: int, country: str) -> List[Dict[str, Any]]:
    """Fetch public holidays from Nager.Date API.
    
    Правильное использование AsyncClient без параметра app:
    - AsyncClient() - правильно
    - AsyncClient(app=app) - НЕПРАВИЛЬНО, вызывает TypeError
    """
    url = f"{NAGER_BASE_URL}/{year}/{country}"
    
    # Правильный способ инициализации AsyncClient из httpx
    # ВАЖНО: НЕ передавать параметр app!
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            # Пробрасываем исключения сети как есть для правильной обработки в API
            raise e
        except httpx.HTTPStatusError as e:
            # Пробрасываем HTTP ошибки как есть для правильной обработки в API
            raise e
        except Exception as e:
            raise ValueError(f"Unexpected error: {e}")


_slug_non_alnum = re.compile(r"[^a-z0-9]+")
_slug_multi_underscore = re.compile(r"_+")


def slugify(text: str, *, max_len: int = 40) -> str:
    t = text.lower()
    t = _slug_non_alnum.sub("_", t)
    t = _slug_multi_underscore.sub("_", t).strip("_")
    if len(t) > max_len:
        t = t[:max_len].rstrip("_")
    return t or "item"


def normalize_nager_item(item: Dict[str, Any], country: str) -> Dict[str, Any]:
    title = str(item.get("localName") or item.get("name") or "").strip() or "Holiday"
    date_iso = str(item.get("date") or "")[:10]
    slug = slugify(title)
    source_id = f"nager_{country}_{date_iso}_{slug}"
    return {
        "title": title,
        "date": date_iso,
        "type": "holiday",
        "status": "todo",
        "source": "nager",
        "meta": {"source_id": source_id},
    }
