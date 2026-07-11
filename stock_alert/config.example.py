# -*- coding: utf-8 -*-
"""
이 파일은 GitHub에 공개로 올라가는 "예시" 파일입니다.
실제 보유 종목/수량/매입가는 여기에 절대 넣지 마세요.

로컬 PC에서 테스트할 때는:
1. 이 파일을 복사해서 config.py 로 저장 (config.py는 .gitignore에 등록되어 있어
   실수로 GitHub에 올라가지 않습니다)
2. config.py 안의 HOLDINGS를 실제 값으로 수정

GitHub Actions(클라우드 자동 실행)에서는 config.py 없이도 동작하도록,
실제 값은 GitHub Secrets의 HOLDINGS_JSON / KAKAO_REST_API_KEY 에 넣습니다.
(Repo Settings -> Secrets and variables -> Actions -> New repository secret)

HOLDINGS_JSON 시크릿에 넣을 값 예시 (한 줄 JSON):
[{"name":"PLUS 글로벌HBM반도체","code":"442580","qty":246,"avg_price":63075}, ...]
"""

HOLDINGS = [
    {"name": "예시 ETF", "code": "000000", "qty": 1, "avg_price": 10000},
]

KAKAO_REST_API_KEY = "여기에_REST_API_키_입력 (로컬 테스트용, GitHub에는 Secret으로)"
KAKAO_REDIRECT_URI = "https://localhost.com"
