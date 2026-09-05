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

def _client_and_model():
    if os.getenv("GROQ_API_KEY"):
        return OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"), "openai/gpt-oss-120b"
    if os.getenv("NVIDIA_API_KEY"):
        # try fallback model that is still alive — groq already handled
        return OpenAI(api_key=os.getenv("NVIDIA_API_KEY"), base_url=os.getenv("NVIDIA_BASE_URL","https://integrate.api.nvidia.com/v1")), os.getenv("NVIDIA_MODEL_FALLBACK_1","deepseek-chat")
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY")), os.getenv("OPENAI_MODEL","gpt-4o-mini")

def summarize(news_title: str, news_desc: str, news_link: str, press: str = "", client=None) -> str:
    if client is None:
        client, model = _client_and_model()
    else:
        _, model = _client_and_model()
        # if client passed, keep its model
        model = "openai/gpt-oss-120b" if os.getenv("GROQ_API_KEY") else model
    user = f"제목: {news_title}\n요약문: {news_desc}\n링크: {news_link}\n언론사: {press}"
    # ensure client uses correct model
    _, m = _client_and_model()
    resp = client.chat.completions.create(model=m, messages=[{"role":"system","content": SYSTEM},{"role":"user","content": user}], temperature=0.7, max_tokens=1800)
    body = resp.choices[0].message.content.strip()
    if "출처" not in body:
        body += f"\n\n출처: {press} {news_link}"
    return body
