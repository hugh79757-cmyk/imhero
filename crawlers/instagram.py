"""Instagram im_hero____ image fetcher — public post pages, no login needed"""
import re, httpx

POSTS = [
    "https://www.instagram.com/im_hero____/p/DczuVtRy_WI/",
    "https://www.instagram.com/im_hero____/p/DcK2cLlxA1H/",
    "https://www.instagram.com/im_hero____/p/DbxeLFkxWEc/",
    "https://www.instagram.com/im_hero____/p/DbuSN2_Su8f/",
    "https://www.instagram.com/im_hero____/p/Dbp3OW9EpgN/",
    "https://www.instagram.com/im_hero____/p/DbpfJMbkbS2/",
    "https://www.instagram.com/im_hero____/p/DbIprckEfRD/",
    "https://www.instagram.com/im_hero____/p/DbHvqXcDP5U/",
    "https://www.instagram.com/im_hero____/p/DbG2TYzy_-6/",
    "https://www.instagram.com/im_hero____/p/Dao5tLBRf91/",
]

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

def _extract(html: str) -> str | None:
    m = re.search(r'property="og:image" content="([^"]+)"', html)
    if m:
        return m.group(1).replace("&amp;", "&")
    m = re.search(r'(https://scontent[^"]+\.jpg[^"]*)', html)
    if m:
        return m.group(1).replace("&amp;", "&").replace("\\u0026","&")
    return None

async def fetch_instagram_images(limit=5):
    urls=[]
    async with httpx.AsyncClient(timeout=12, headers={"User-Agent": UA}, follow_redirects=True) as c:
        for p in POSTS:
            if len(urls)>=limit: break
            try:
                r=await c.get(p)
                if r.status_code!=200: continue
                u=_extract(r.text)
                if u and u not in urls:
                    urls.append(u)
            except Exception:
                continue
    return urls

def fetch_images_sync(limit=5):
    import asyncio
    return asyncio.run(fetch_instagram_images(limit))
