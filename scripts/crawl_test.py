import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from crawlers.naver_news import search_news
from config.settings import Settings

async def main():
    s=Settings()
    items=await search_news("임영웅", display=5, client_id=s.NAVER_CLIENT_ID, client_secret=s.NAVER_CLIENT_SECRET)
    for i, it in enumerate(items,1):
        print(f"{i}. {it.title}")
        print(f"   {it.description[:80]}")
        print(f"   {it.link} | {it.pubDate}")
if __name__=="__main__": asyncio.run(main())
