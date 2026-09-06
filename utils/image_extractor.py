"""og:image extractor for Naver news article"""
import re, httpx
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
async def fetch_og_image(url: str) -> str | None:
    if not url: return None
    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": UA}, follow_redirects=True) as c:
            r=await c.get(url)
            if r.status_code!=200: return None
            html=r.text
            m=re.search(r'property="og:image" content="([^"]+)"', html)
            if m: return m.group(1).replace("&amp;","&")
            m=re.search(r'property="og:image:secure_url" content="([^"]+)"', html)
            if m: return m.group(1).replace("&amp;","&")
    except Exception:
        return None
    return None
