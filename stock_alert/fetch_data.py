# -*- coding: utf-8 -*-
"""
네이버 금융(모바일/폴링) 비공식 API로 국내 상장 ETF 현재가·뉴스를 조회합니다.

주의: 이 API들은 네이버가 공식 문서화한 API가 아니라, 네이버페이 증권 앱/웹이
내부적으로 쓰는 엔드포인트입니다. 네이버 쪽 사정으로 응답 구조가 바뀔 수 있으니,
Claude Code에서 실제로 실행해보고 응답 JSON 구조가 다르면 그에 맞게 파싱 부분을
같이 고쳐야 합니다. (print(res.json())으로 실제 구조 확인 추천)
"""

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get_current_price(code: str) -> dict:
    """실시간(20분 지연) 현재가 조회"""
    url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{code}"
    res = requests.get(url, headers=HEADERS, timeout=5)
    res.raise_for_status()
    data = res.json()
    item = data["result"]["areas"][0]["datas"][0]
    return {
        "price": int(item["nv"]),         # 현재가
        "change": int(item["cv"]),        # 전일대비 변동
        "change_rate": float(item["cr"]), # 등락률 (%)
    }


def get_news(code: str, count: int = 2) -> list:
    """종목 관련 최신 뉴스 조회"""
    url = f"https://m.stock.naver.com/api/news/stock/{code}?pageSize={count}&page=1"
    res = requests.get(url, headers=HEADERS, timeout=5)
    res.raise_for_status()
    items = res.json()
    news_list = []
    for it in items[:count]:
        news_list.append({
            "title": it.get("title", "").replace("<b>", "").replace("</b>", ""),
            "date": it.get("datetime", ""),
            "office": it.get("officeName", ""),
        })
    return news_list


if __name__ == "__main__":
    # 단독 실행 시 테스트: python fetch_data.py
    test_code = "442580"
    print("== 현재가 ==")
    print(get_current_price(test_code))
    print("== 뉴스 ==")
    for n in get_news(test_code):
        print(n)
