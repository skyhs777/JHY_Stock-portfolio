# -*- coding: utf-8 -*-
"""
카카오톡 '나에게 보내기' 메시지 전송.
kakao_auth.py 를 먼저 1회 실행해서 kakao_token.json 이 있어야 동작합니다.
access_token은 몇 시간 안에 만료되므로, 매번 refresh_token으로 갱신 후 전송합니다.
"""

import json
import os
import requests

TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kakao_token.json")


def _load_token() -> dict:
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_token(token_data: dict) -> None:
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)


def refresh_access_token(rest_api_key: str) -> str:
    token_data = _load_token()
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": rest_api_key,
        "refresh_token": token_data["refresh_token"],
    }
    res = requests.post(url, data=data)
    res.raise_for_status()
    new_token = res.json()
    token_data["access_token"] = new_token["access_token"]
    if "refresh_token" in new_token:
        token_data["refresh_token"] = new_token["refresh_token"]
    _save_token(token_data)
    return token_data["access_token"]


def send_to_me(rest_api_key: str, text: str, web_url: str = "https://claude.ai") -> dict:
    access_token = refresh_access_token(rest_api_key)
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    template = {
        "object_type": "text",
        "text": text,
        "link": {"web_url": web_url, "mobile_web_url": web_url},
    }
    data = {"template_object": json.dumps(template, ensure_ascii=False)}
    res = requests.post(url, headers=headers, data=data)
    res.raise_for_status()
    return res.json()
