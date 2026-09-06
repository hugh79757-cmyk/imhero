"""Tistory publisher — hugh79757 lawsofhumannature auto-publish (Aside/Playwright)

SKILL: /Users/twinssn/.config/opencode/skills/tistory-publish/SKILL.md
핵심: tinymce.save() 필수, DKAPTCHA 음성은 voice_captcha_pool mp3 → whisper medium, 비공개→공개 토글은 open20 체크 후 publish
"""
import re, pathlib, asyncio, os
from config.settings import Settings

# lawsofhumannature 카테고리 (2026-09-06 실측)
CATEGORY_MAP = {
    "concert": "임영웅 콘서트 소식",
    "news": "임영웅 뉴스",
    "song": "임영웅 노래 모음",
    "fan": "임영웅 팬클럽",
}
DEFAULT_CATEGORY = "임영웅 콘서트 소식"

def pick_category(title: str) -> str:
    t=title or ""
    if "노래" in t or "음원" in t: return CATEGORY_MAP["song"]
    if "팬클럽" in t or "영웅시대" in t: return CATEGORY_MAP["fan"]
    if "뉴스" in t: return CATEGORY_MAP["news"]
    return CATEGORY_MAP["concert"]

async def publish_one(title: str, body_html: str, category: str="") -> dict:
    """Aside REPL 없이 호출되는 headless 경로 — 실제 발행은 scripts/auto_publish.py (playwright) 가 담당.
    이 함수는 pipeline에서 호출 시 dry_run=false 일 때 auto_publish.py로 위임하기 위한 thin wrapper.
    """
    # pipeline이 직접 호출 시에는 subprocess로 auto_publish.py 위임
    import subprocess, json, tempfile, pathlib
    tmp = pathlib.Path(tempfile.gettempdir()) / "imhero_publish.json"
    tmp.write_text(json.dumps({"title": title, "body": body_html, "category": category or pick_category(title)}, ensure_ascii=False), encoding="utf-8")
    # auto_publish.py는 단일 글 발행 모드 지원
    result = subprocess.run(["/Users/twinssn/Projects2/imhero/.venv/bin/python", "scripts/auto_publish.py", "--one", str(tmp)], capture_output=True, text=True, timeout=180)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
