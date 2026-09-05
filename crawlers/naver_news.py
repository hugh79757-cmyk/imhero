"""Naver News Search API — 임영웅 뉴스 수집"""
import httpx
from dataclasses import dataclass
from typing import List
from datetime import datetime

API_URL = "https://openapi.naver.com/v1/search/news.json"

@dataclass
class NewsItem:
    title: str
    originallink: str
    link: str
    description: str
    pubDate: str
    press: str = ""

    def to_dict(self):
        return self.__dict__

async def search_news(query: str, display: int = 20, start: int = 1, sort: str = "date",
                       client_id: str = "", client_secret: str = "") -> List[NewsItem]:
    """Naver Search API 호출 — sort=date(최신순) 권장"""
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {"query": query, "display": display, "start": start, "sort": sort}
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.get(API_URL, headers=headers, params=params)
        r.raise_for_status()
        data = r.json()
        items = []
        for it in data.get("items", []):
            # title/description은 <b> 태그 포함 — 제거
            import re
            clean = lambda s: re.sub(r"</?b>", "", s or "")
            items.append(NewsItem(
                title=clean(it.get("title")),
                originallink=it.get("originallink",""),
                link=it.get("link",""),
                description=clean(it.get("description")),
                pubDate=it.get("pubDate",""),
                press=it.get("originallink","").split("/")[2] if it.get("originallink") else "",
            ))
        return items

def search_news_sync(*a, **kw):
    import asyncio
    return asyncio.run(search_news(*a, **kw))
