"""LLM 요약 — 뉴스 1건 → 블로그 글 본문"""
from openai import OpenAI
import os

SYSTEM = """너는 임영웅 팬블로그(@You're_Hero____) 에디터다.
입력된 뉴스 원문을 800~1200자로 요약한다.
- 제목은 별도 생성하지 말고 본문만 작성
- 구조: 도입(2문장) → 핵심 내용(h2 2개, 각 3~4문장) → 마무리(팬 메시지 2문장)
- 본문 중간에는 출처/원문/링크 어떤 형태로도 언급 금지 — 몰입 끊김 방지
- 허구 금지, 원문 없는 내용 지어내지 말기
- 어투: 팬 친화, 따뜻함
- 링크는 출력하지 말라 — 원문 링크는 시스템이 하단에 한 번만 추가한다
"""

def _client_and_model():
    if os.getenv("GROQ_API_KEY"):
        return OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1"), "openai/gpt-oss-120b"
    if os.getenv("NVIDIA_API_KEY"):
        # try fallback model that is still alive — groq already handled
        return OpenAI(api_key=os.getenv("NVIDIA_API_KEY"), base_url=os.getenv("NVIDIA_BASE_URL","https://integrate.api.nvidia.com/v1")), os.getenv("NVIDIA_MODEL_FALLBACK_1","deepseek-chat")
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY")), os.getenv("OPENAI_MODEL","gpt-4o-mini")

def _try(client, model, user):
    resp = client.chat.completions.create(model=model, messages=[{"role":"system","content": SYSTEM},{"role":"user","content": user}], temperature=0.7, max_tokens=1800)
    return resp.choices[0].message.content.strip()

def _strip_mid_source(text: str) -> str:
    import re
    # 중간에 LLM이 넣은 출처/원문/링크 줄 제거 — 하단 원문은 pipeline이 한 번만 추가
    text = re.sub(r'\n+출처\s*[:：].*', '', text)
    text = re.sub(r'\n+원문\s*[:：].*', '', text)
    # press + http 혼합 줄도 제거 (예: 출처: www.newsis.com https://...)
    text = re.sub(r'\n+https?://\S+\s*$', '', text, flags=re.MULTILINE)
    return text.strip()

def summarize(news_title: str, news_desc: str, news_link: str, press: str = "", client=None) -> str:
    user = f"제목: {news_title}\n요약문: {news_desc}\n링크: {news_link}\n언론사: {press}"
    # tier1 groq
    groq_key=os.getenv("GROQ_API_KEY")
    if groq_key:
        for gm in ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]:
            try:
                c=OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
                body=_try(c, gm, user)
                return _strip_mid_source(body)
            except Exception as e:
                if "429" in str(e) or "RateLimit" in str(e):
                    print(f"groq {gm} 429: {e}")
                    continue
                raise
    # tier2 nvidia
    nvidia_key=os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        try:
            c=OpenAI(api_key=nvidia_key, base_url=os.getenv("NVIDIA_BASE_URL","https://integrate.api.nvidia.com/v1"))
            for m in ["deepseek-ai/deepseek-v3.1","meta/llama-3.1-70b-instruct","openai/gpt-oss-120b"]:
                try:
                    body=_try(c, m, user)
                    return _strip_mid_source(body)
                except Exception as e2:
                    if "410" not in str(e2) and "404" not in str(e2): raise
                    continue
        except Exception as e:
            print(f"nvidia fallback fail: {e}")
    # tier3 openai (explicit, bypass groq)
    try:
        c3=OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        for m3 in [os.getenv("OPENAI_MODEL","gpt-4o-mini"), "gpt-4o", "gpt-4o-mini-2024-07-18", "gpt-3.5-turbo"]:
            try:
                body=_try(c3, m3, user)
                return _strip_mid_source(body)
            except Exception as e3:
                if "404" not in str(e3) and "model_not_found" not in str(e3):
                    raise
                continue
        raise Exception(f"openai all models failed")
    except Exception as e:
        print(f"openai tier fail: {e}")
        raise
