"""imhero pipeline — Naver News → summarize → draft (+image)"""
import asyncio, pathlib, re, os, datetime
from config.settings import Settings
from crawlers.naver_news import search_news
from crawlers.instagram import fetch_instagram_images
from generators.summarizer import summarize
from utils.image_extractor import fetch_og_image

DRAFT_DIR = pathlib.Path("data/drafts")

def _slug(s: str) -> str:
    s=re.sub(r'[^\w가-힣]+','-',s).strip('-')[:40]
    return s or "draft"

async def run(query="임영웅", limit=5, dry_run=False):
    s=Settings()
    errs=s.validate()
    if errs:
        print("ENV missing:", errs); return
    items=await search_news(query, display=limit, client_id=s.NAVER_CLIENT_ID, client_secret=s.NAVER_CLIENT_SECRET)
    # 제목에 임영웅 없는 연관 뉴스(고양시장 등) 제외
    items = [it for it in items if "임영웅" in it.title]
    print(f"수집 {len(items)}건 (임영웅 필터 후)")
    # Instagram pool
    ig_urls=await fetch_instagram_images(limit=limit)
    print(f"인스타 {len(ig_urls)}장")
    # og:image per news
    og_images=[]
    for it in items:
        og=await fetch_og_image(it.originallink or it.link)
        og_images.append(og)
        print(f" - {it.title[:40]} | og:{bool(og)} | press:{it.press}")

    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    for i,it in enumerate(items):
        body=summarize(it.title, it.description, it.link, it.press)
        # 중간 출처/원문 줄 제거 (LLM이 넣었을 경우) — 하단에만 한 번
        body = re.sub(r'\n+출처\s*[:：].*', '', body)
        body = re.sub(r'\n+원문\s*[:：].*', '', body)
        body = body.strip()
        # pick image: news og at top + instagram second (round-robin)
        news_img = og_images[i]
        ig_img = ig_urls[i % len(ig_urls)] if ig_urls else ""
        if news_img:
            body = f'<p><img src="{news_img}" alt="임영웅 뉴스" style="width:100%;max-width:700px;" /></p>\n\n' + body
        # always append instagram image as second if available and different
        if ig_img and ig_img != news_img:
            body += f'\n\n<p><img src="{ig_img}" alt="임영웅 인스타그램" style="width:100%;max-width:700px;" /></p>\n<p><em>사진: 임영웅 공식 인스타그램 @im_hero____</em></p>'
        # save — 원문은 글 하단에 한 번만
        slug=_slug(it.title)
        ts=datetime.datetime.now().strftime("%Y%m%d_%H%M")
        fname=DRAFT_DIR / f"{ts}_{i+1}_{slug}.md"
        fname.write_text(f"# {it.title}\n\n{body}\n\n원문: {it.link}\n", encoding="utf-8")
        print(f"draft {fname} {len(body)}자")
    print("완료", DRAFT_DIR)

if __name__=="__main__":
    import sys
    publish="--publish" in sys.argv
    args=[a for a in sys.argv[1:] if not a.startswith("--")]
    lim=int(args[0]) if args else 5
    asyncio.run(run(limit=lim, dry_run=False))
    if publish:
        # 발행 단계 — 최근 draft 중 원문 미발행 5건 순차
        import pathlib, json, subprocess
        drafts=sorted(pathlib.Path("data/drafts").glob("*.md"))[-5:]
        for f in drafts:
            txt=f.read_text(encoding="utf-8")
            title=txt.splitlines()[0].lstrip("# ").strip()
            body="\n".join(txt.splitlines()[1:])
            # body는 이미 원문 1회 포함 — 그대로 전달
            print(f" publishing {f.name} ...")
            # publisher thin wrapper가 auto_publish.py --one 호출
            from publishers.tistory import publish_one as pub
            import asyncio as _aio
            res=_aio.run(pub(title, body, "임영웅 콘서트 소식"))
            print(res.get("stdout","")[:800])
            if res.get("returncode",1)!=0:
                print(f" publish fail {f.name} {res.get('stderr','')[:500]}")
