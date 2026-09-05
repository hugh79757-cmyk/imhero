"""LLM 요약 — 뉴스 1건 → 블로그 글 본문"""
from openai import OpenAI
import os

SYSTEM = """너는 임영웅 팬블로그(@You're_Hero____) 에디터다.
입력된 뉴스 원문을 800~1200자로 요약하고, 출처와 원문 링크를 명시한다.
- 제목은 별도 생성하지 말고 본문만 작성
- 구조: 도입(2문장) → 핵심 내용(h2 2개, 각 3~4문장) → 마무리(팬 메시지 2문장)
- 마지막에 '출처: <press> <link>' 한 줄
- 허구 금지, 원문 없는 내용 지어내지 말기
- 어투: 팬 친화, 따뜻함
"""

def summarize(news_title: str, news_desc: str, news_link: str, press: str = "", client: OpenAI | None = None) -> str:
    if client is None:
        key = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        base = os.getenv("NVIDIA_BASE_URL","https://integrate.api.nvidia.com/v1") if os.getenv("NVIDIA_API_KEY") else None
        client = OpenAI(api_key=key, base_url=base) if base else OpenAI(api_key=key)
    user = f"제목: {news_title}\n요약문: {news_desc}\n링크: {news_link}\n언론사: {press}"
    resp = client.chat.completions.create(
        model=os.getenv("LLM_MODEL","meta/llama-3.1-70b-instruct"),
        messages=[{"role":"system","content": SYSTEM},{"role":"user","content": user}],
        temperature=0.7,
        max_tokens=1800,
    )
    body = resp.choices[0].message.content.strip()
    if "출처" not in body:
        body += f"\n\n출처: {press} {news_link}"
    return body
