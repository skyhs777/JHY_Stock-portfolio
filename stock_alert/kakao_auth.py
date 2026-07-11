# -*- coding: utf-8 -*-
"""
카카오톡 '나에게 보내기' API를 쓰기 위한 최초 1회 로그인 스크립트.

사전 준비 (카카오 디벨로퍼스, https://developers.kakao.com):
1. 내 애플리케이션 -> 애플리케이션 추가하기 (이름은 자유롭게, 예: 주식알림)
2. 앱 선택 -> 카카오 로그인 -> 활성화 ON
3. 카카오 로그인 -> 동의항목 -> "카카오톡 메시지 전송" 항목 선택 후 저장
4. 카카오 로그인 -> Redirect URI 등록 -> https://localhost.com 추가
   (config.py의 KAKAO_REDIRECT_URI 와 반드시 동일해야 함)
5. 앱 요약 정보에서 "REST API 키" 복사 -> config.py 의 KAKAO_REST_API_KEY 에 붙여넣기

실행 방법:
    python kakao_auth.py
안내에 따라 브라우저에서 로그인 -> 리다이렉트된 주소창의 code= 뒷부분을 복사해서
터미널에 붙여넣으면 kakao_token.json 파일이 생성됩니다.
이 토큰 파일은 최초 1회만 만들면 되고, 이후에는 main.py가 자동으로 갱신합니다.
"""

import json
import webbrowser
import requests

from config import KAKAO_REST_API_KEY, KAKAO_REDIRECT_URI

TOKEN_FILE = "kakao_token.json"


def get_auth_code() -> str:
    auth_url = (
        "https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_REST_API_KEY}"
        f"&redirect_uri={KAKAO_REDIRECT_URI}"
        "&response_type=code"
        "&scope=talk_message"
    )
    print("브라우저가 열리지 않으면 아래 URL을 직접 복사해서 접속하세요:")
    print(auth_url)
    webbrowser.open(auth_url)
    print()
    print("로그인 후 리다이렉트된 주소가 다음과 비슷한 형태로 보일 겁니다:")
    print("  https://localhost.com/?code=AbCdEfG12345...")
    code = input("주소창의 'code=' 뒤에 있는 값만 복사해서 붙여넣으세요: ").strip()
    return code


def issue_token(code: str) -> dict:
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }
    res = requests.post(url, data=data)
    res.raise_for_status()
    token_data = res.json()
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)
    print(f"\n토큰 저장 완료: {TOKEN_FILE}")
    return token_data


if __name__ == "__main__":
    auth_code = get_auth_code()
    issue_token(auth_code)
