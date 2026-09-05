"""imhero pipeline — Naver News → summarize → draft/publish"""
import asyncio
from config.settings import Settings
from crawlers.naver_news import search_news
from generators.summarizer import summarize

async def run(query="임영웅", limit=15, dry_run=True):
    s = Settings()
    errs = s.validate()
    if errs:
        print("ENV missing:", errs)
        return
    items = await search_news(query, display=limit, client_id=s.NAVER_CLIENT_ID, client_secret=s.NAVER_CLIENT_SECRET)
    print(f"수집 {len(items)}건")
    for it in items[:3]:
        print(f" - {it.title} | {it.press} | {it.link}")
    if dry_run:
        print("dry_run — 발행 스킵")
        return
    # TODO: LLM 요약 → Tistory 발행 (Aside)
    for it in items:
        body = summarize(it.title, it.description, it.link, it.press)
        print(f"요약 {it.title[:30]}... {len(body)}자")
        # publish ...

if __name__ == "__main__":
    asyncio.run(run())
