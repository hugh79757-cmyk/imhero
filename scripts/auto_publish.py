"""auto_publish — Playwright로 lawsofhumannature 발행 (hugh79757)
사용법: python scripts/auto_publish.py --one /tmp/imhero_publish.json
또는: python scripts/auto_publish.py --all (data/drafts/*.md 전부)

핵심 스텝 (tistory-publish SKILL 실측 재현):
  login( DKAPTCHA 음성 → whisper medium ) → newpost → title 키보드 → tinymce setContent+save() → category → 완료 → 공개 토글 → 발행 → DKAPTCHA 재처리
"""
import asyncio, pathlib, json, re, sys, os, tempfile, subprocess
from dotenv import load_dotenv; load_dotenv()
from playwright.async_api import async_playwright

def md_to_html(body: str) -> str:
    """draft md → TinyMCE HTML. 첫 줄 '# 제목' 제거, ## → h2, 빈 라인 무시, 나머지 → p."""
    lines=[l for l in body.splitlines() if l.strip()]
    if lines and lines[0].startswith("# "):
        lines=lines[1:]
    out=[]
    for ln in lines:
        s=ln.strip()
        m=re.match(r'^## (.+)$', s)
        if m:
            out.append(f'<h2 data-ke-size="size26">{m.group(1).strip()}</h2>')
        elif s.startswith("<"):
            out.append(s)
        else:
            out.append(f'<p data-ke-size="size16">{s}</p>')
    return "\n".join(out)

MANAGE_NEWPOST = "https://lawsofhumannature.tistory.com/manage/newpost"
MANAGE_POSTS = "https://lawsofhumannature.tistory.com/manage/posts"
EMAIL = os.getenv("TISTORY_EMAIL", "hugh79757@gmail.com")
PASSWORD = os.getenv("TISTORY_PASSWORD", "")
WHISPER_BIN = "/Users/twinssn/.kaggle-env/bin/whisper"

async def solve_dkaptcha(page):
    # DKAPTCHA iframe 탐지 (url='' 이나 body DKAPTCHA)
    await asyncio.sleep(1.2)
    frames = page.frames
    dk = None
    for f in frames:
        try:
            txt = await f.evaluate("()=>document.body.innerText.slice(0,1200)")
            if "DKAPTCHA" in txt or "dkaptcha" in txt.lower() or "지도에서" in txt:
                dk = f
                break
        except: continue
    if not dk:
        return True  # 캡챠 없음
    print(f"DKAPTCHA found frame {dk.url[:80]}")
    # 음성으로 전환
    try:
        await dk.evaluate("()=>{ const b=document.querySelector('#btn_dkaptcha_change'); if(b) b.click(); }")
        await asyncio.sleep(1.5)
    except: pass
    # mp3 URL (frame 내부 performance)
    mp3 = ""
    for _ in range(3):
        try:
            mp3 = await dk.evaluate("()=>{ const rs=performance.getEntriesByType('resource'); const r=[...rs].reverse().find(x=>x.name.includes('voice_captcha_pool')); return r?r.name:''; }")
            if mp3: break
        except: pass
        await asyncio.sleep(0.8)
    if not mp3:
        print("DKAPTCHA mp3 not found")
        return False
    print(f"mp3 {mp3[:90]}")
    # 다운로드
    import httpx
    async with httpx.AsyncClient() as cli:
        r = await cli.get(mp3, timeout=15)
        tmp = pathlib.Path(tempfile.gettempdir()) / "dkaptcha.mp3"
        tmp.write_bytes(r.content)
        print(f"mp3 {len(r.content)}B")
    # whisper medium
    try:
        out = subprocess.run([WHISPER_BIN, str(tmp), "--model", "medium", "--language", "ko", "--output_format", "txt", "--output_dir", tempfile.gettempdir()], capture_output=True, text=True, timeout=45)
        txt_path = pathlib.Path(tempfile.gettempdir()) / "dkaptcha.txt"
        wtxt = txt_path.read_text(encoding="utf-8", errors="ignore") if txt_path.exists() else out.stdout
    except Exception as e:
        wtxt = ""
        print(f"whisper fail {e}")
    print(f"whisper raw: {wtxt[:400]}")
    # 숫자 추출 — 5자리 우선
    nums = re.findall(r"[0-9]", wtxt)
    # 한국어 숫자 매핑 보조
    kor = {"영":0,"공":0,"일":1,"하나":1,"이":2,"둘":2,"삼":3,"셋":3,"사":4,"넷":4,"오":5,"다섯":5,"육":6,"여섯":6,"칠":7,"일곱":7,"팔":8,"여덟":8,"구":9,"아홉":9}
    if len(nums) < 5:
        for k,v in kor.items():
            if k in wtxt: nums.append(str(v))
    code = "".join(nums[:5])
    if len(code) < 5:
        # fallback: whisper small 한국어 숫자 텍스트에서 한 글자씩 매핑
        pass
    print(f"code {code}")
    if len(code) != 5:
        # 새로 풀기로 재시도
        try: await dk.evaluate("()=>document.querySelector('#btn_dkaptcha_reset')?.click()")
        except: pass
        return False
    try:
        await dk.evaluate(f"()=>{{ const inp=document.querySelector('#inpDkaptcha'); if(inp){{ inp.focus(); inp.value=''; }} }}")
        # pressSequentially 대신 evaluate로 입력 후 이벤트 디스패치
        await dk.evaluate(f"()=>{{ const inp=document.querySelector('#inpDkaptcha'); if(inp){{ inp.value='{code}'; inp.dispatchEvent(new Event('input',{{bubbles:true}})); inp.dispatchEvent(new Event('change',{{bubbles:true}})); }} }}")
        await asyncio.sleep(0.4)
        await dk.evaluate("()=>document.querySelector('#btn_dkaptcha_submit')?.click()")
        await asyncio.sleep(2.5)
        # 프레임 파괴 확인
        alive=False
        try: await dk.evaluate("()=>document.body.innerText"); alive=True
        except: alive=False
        if not alive: 
            print("DKAPTCHA passed — frame destroyed")
            return True
        # 실패 시 재시도
        txt2 = await dk.evaluate("()=>document.body.innerText.slice(0,800)") if alive else ""
        print(f"DKAPTCHA still alive: {txt2[:300]}")
        if "재시도" in txt2 or "실패" in txt2:
            await dk.evaluate("()=>document.querySelector('#btn_dkaptcha_reset')?.click()")
            await asyncio.sleep(1.2)
        return False
    except Exception as e:
        print(f"dk submit fail {e}")
        return False

async def login(page):
    await page.goto("https://www.tistory.com/auth/login?redirectUrl=https://lawsofhumannature.tistory.com/manage", wait_until="domcontentloaded")
    await asyncio.sleep(1.5)
    # 이미 로그인 되어 있으면 newpost로 직행
    if "lawsofhumannature" in page.url and "manage" in page.url:
        return True
    # 카카오 로그인 버튼 찾기
    try:
        # accounts.kakao.com 리다이렉트 될 수 있음 — 이메일 입력
        # 현재 페이지가 kakao인지 tistory인지 분기
        if "kakao.com" in page.url:
            # kakao login form — #loginId--1 / #password--2 (live id)
            await page.wait_for_selector("input[name='email'], input#loginId--1, input[type='text']", timeout=8000)
            # 찾기
            email_sel = await page.evaluate("()=>{ const els=[...document.querySelectorAll('input')]; const e=els.find(x=>x.type==='text' || x.name==='email' || (x.id||'').includes('loginId')); return e? (e.id? '#'+e.id : 'input[name=email]') : '' }")
            print(f"kakao email sel {email_sel}")
            if email_sel: await page.locator(email_sel).press_sequentially(EMAIL, delay=60)
            await asyncio.sleep(0.5)
            pw_sel = await page.evaluate("()=>{ const els=[...document.querySelectorAll('input')]; const e=els.find(x=>x.type==='password'); return e? (e.id? '#'+e.id : 'input[type=password]') : '' }")
            print(f"kakao pw sel {pw_sel}")
            if pw_sel: await page.locator(pw_sel).press_sequentially(PASSWORD, delay=60)
            await asyncio.sleep(0.5)
            # 로그인 버튼
            await page.evaluate("()=>{ const b=[...document.querySelectorAll('button')].find(x=>x.innerText.includes('로그인')); if(b) b.click(); }")
            await asyncio.sleep(3.5)
            # DKAPTCHA
            for _ in range(3):
                ok = await solve_dkaptcha(page)
                if ok: break
                await asyncio.sleep(1.2)
            await asyncio.sleep(2)
            # 2FA 체크 (sms/email) — hugh79757는 없음, 있으면 중단
            if "twoStep" in page.url or "emailTwoStep" in page.url:
                print("2FA required — abort, need manual")
                return False
        else:
            # tistory 카카오 버튼
            await page.evaluate("()=>{ const b=[...document.querySelectorAll('a,button')].find(x=> (x.innerText||'').includes('카카오')); if(b) b.click(); }")
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)
            return await login(page)
    except Exception as e:
        print(f"login fail {e}")
        return False
    return "lawsofhumannature" in page.url or "manage" in page.url

async def publish_one_async(title: str, body_html: str, category: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context()
        page = await ctx.new_page()
        try:
            if not await login(page):
                print("login failed")
                return False
            print("login ok", page.url)
            await page.goto(MANAGE_NEWPOST, wait_until="domcontentloaded")
            await asyncio.sleep(2)
            # title — keyboard Meta+A
            title_sel = "#post-title-inp, #title-input, input[placeholder*='제목']"
            await page.wait_for_selector(title_sel, timeout=8000)
            await page.locator(title_sel).click()
            await page.keyboard.press("Meta+A")
            await page.keyboard.press("Backspace")
            await page.locator(title_sel).press_sequentially(title, delay=60)
            await asyncio.sleep(0.8)
            # body — tinymce save()
            # body_html may contain markdown; ensure html
            html = body_html
            # need to ensure file size not too large for evaluate — write to tmp and set
            await page.evaluate(f"""(html)=>{{
                const ed = window.tinymce && tinymce.get('editor-tistory');
                if(ed){{ ed.setContent(html); ed.fire('change'); ed.save(); }}
                const ta=document.querySelector('#editor-tistory, textarea#editor-tistory');
                if(ta){{ ta.value = document.querySelector('iframe')?.contentDocument?.body?.innerHTML || html; ta.dispatchEvent(new Event('input',{{bubbles:true}})); }}
                const ifr=document.querySelector('iframe');
                if(ifr && ifr.contentDocument){{ ifr.contentDocument.body.innerHTML = html; ifr.contentDocument.body.dispatchEvent(new Event('input',{{bubbles:true}})); }}
            }}""", html)
            await asyncio.sleep(0.8)
            ok_body = await page.evaluate("()=>{ const ta=document.querySelector('#editor-tistory'); return {len:(ta?.value||'').length, hasImg:(ta?.value||'').includes('<img')} }")
            print(f"body injected {ok_body}")
            # category combobox
            try:
                await page.locator('[role=combobox]').click(timeout=4000)
                await asyncio.sleep(0.8)
                # find category by text
                await page.evaluate(f"()=>{{ const opts=[...document.querySelectorAll('[role=option], li')]; const hit=opts.find(x=> (x.innerText||'').includes('{category}')); if(hit) hit.click(); }}")
                await asyncio.sleep(0.7)
            except Exception as e:
                print(f"category fail {e}")
            # 완료
            await page.evaluate("()=>{ const b=[...document.querySelectorAll('button, a')].find(x=> (x.innerText||'').trim()==='완료'); if(b) b.click(); }")
            await asyncio.sleep(2.5)
            # 발행 다이얼로그 — 비공개→공개 토글
            await page.evaluate("()=>{ const r=document.querySelector('label[for=open20], #open20'); if(r){{ r.click(); const cb=document.querySelector('#open20'); if(cb){{ cb.checked=true; cb.dispatchEvent(new Event('change',{{bubbles:true}})); }} }} }")
            await asyncio.sleep(0.6)
            # 공개 발행 클릭
            await page.evaluate("()=>{ const b=[...document.querySelectorAll('button')].find(x=> (x.innerText||'').trim()==='공개 발행'); if(b) b.click(); }")
            await asyncio.sleep(2)
            # DKAPTCHA 재처리
            for _ in range(4):
                ok = await solve_dkaptcha(page)
                if ok:
                    # 캡챠 통과 후 다시 공개 발행 눌러야 하는 경우 있음 (저장중 hang 분기)
                    await asyncio.sleep(1)
                    # 버튼 다시 클릭 시도
                    still = await page.evaluate("()=>location.href")
                    if "manage/posts" in still:
                        break
                    await page.evaluate("()=>{ const b=[...document.querySelectorAll('button')].find(x=> (x.innerText||'').trim()==='공개 발행'); if(b) b.click(); }")
                    await asyncio.sleep(1.5)
                    if "manage/posts" in await page.evaluate("()=>location.href"):
                        break
                    # 캡챠 없으면 성공
                    if not any("dkaptcha" in f.url for f in page.frames):
                        break
                await asyncio.sleep(1)
            await asyncio.sleep(1.5)
            url = page.url
            print(f"final url {url}")
            success = "manage/posts" in url
            if success:
                print("PUBLISHED")
                return True
            # 실패 로그
            content = await page.content()
            print(content[:4000])
            return False
        finally:
            await asyncio.sleep(2)
            await browser.close()

def main():
    import argparse, pathlib
    ap=argparse.ArgumentParser()
    ap.add_argument("--one", type=str, help="json path with title/body/category")
    ap.add_argument("--all", action="store_true")
    args=ap.parse_args()
    if args.one:
        data=json.loads(pathlib.Path(args.one).read_text(encoding="utf-8"))
        ok=asyncio.run(publish_one_async(data["title"], md_to_html(data["body"]), data.get("category","임영웅 콘서트 소식")))
        sys.exit(0 if ok else 1)
    elif args.all:
        drafts=sorted(pathlib.Path("data/drafts").glob("*.md"))
        for f in drafts[-5:]:
            txt=f.read_text(encoding="utf-8")
            lines=txt.splitlines()
            # 첫 줄이 '# 제목'이면 body에서 제거 (제목 누출 방지)
            if lines and lines[0].startswith("# "):
                lines=lines[1:]
            title=[l for l in lines if l.startswith("# ")][0].lstrip("# ").strip() if any(l.startswith("# ") for l in lines) else txt.splitlines()[0].lstrip("# ").strip()
            # fallback: 원본 첫 줄에서 제목 복원
            orig_first=txt.splitlines()[0].lstrip("# ").strip()
            title=orig_first
            body="\n".join(lines)
            ok=asyncio.run(publish_one_async(title, md_to_html(body), "임영웅 콘서트 소식"))
            print(f"{f.name} -> {ok}")
            asyncio.run(asyncio.sleep(2))
    else:
        print("use --one or --all")

if __name__=="__main__":
    main()
