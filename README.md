# imhero - 임영웅 뉴스 큐레이션 → 티스토리 @You're_Hero____ 자동 발행

하루 15개 뉴스 요약 발행. 소스: 네이버 뉴스 / 팬카페 / 유튜브(물고기뮤직) / 인스타(im_hero____)

- Crawlers: naver_news, fan_cafe, youtube, instagram (Aside)
- Pipeline: crawl → LLM summarize → Tistory publish
- Scheduler: macOS launchd hourly
- Target: https://youaremyhero.tistory.com (참여중 @You're_Hero____)

TV-show 파이프라인 패턴 재사용. Pages/Workers 없음 — 로컬 MVP.
