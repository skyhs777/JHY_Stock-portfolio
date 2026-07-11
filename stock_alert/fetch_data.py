# -*- coding: utf-8 -*-
"""
네이버 금융(모바일/폴링) 비공식 API로 국내 상장 ETF 현재가·뉴스를 조회합니다.

주의: 이 API들은 네이버가 공식 문서화한 API가 아니라, 네이버페이 증권 앱/웹이
내부적으로 쓰는 엔드포인트입니다. 네이버 쪽 사정으로 응답 구조가 바뀔 수 있으니,
Claude Code에서 실제로 실행해보고 응답 JSON 구조가 다르면 그에 맞게 파싱 부분을
같이 고쳐야 합니다. (print(res.json())으로 실제 구조 확인 추천)
"""

import re
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _to_number(value):
    """'354,000' 같은 콤마 포함 문자열/숫자를 float으로 변환"""
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace(",", ""))


def get_current_price(code: str) -> dict:
    """네이버 실시간 시세 조회. 응답 필드는 closePrice / compareToPreviousClosePrice /
    fluctuationsRatio 이며 값은 콤마가 포함된 문자열로 올 수 있어 숫자 변환이 필요하다."""
    url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{code}"
    res = requests.get(url, headers=HEADERS, timeout=5)
    res.raise_for_status()
    data = res.json()

    # 응답 최상위 구조가 버전에 따라 다를 수 있어 두 가지 형태를 모두 시도
    if "datas" in data:
        item = data["datas"][0]
    else:
        item = data["result"]["areas"][0]["datas"][0]

    return {
        "price": int(_to_number(item["closePrice"])),
        "change": int(_to_number(item["compareToPreviousClosePrice"])),
        "change_rate": _to_number(item["fluctuationsRatio"]),
    }


def get_news(name: str, count: int = 2) -> list:
    """구글 뉴스 RSS로 종목명 관련 최신 뉴스 조회 (네이버 비공식 API보다 안정적)"""
    query = quote(f"{name} ETF")
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    res = requests.get(url, headers=HEADERS, timeout=5)
    res.raise_for_status()

    root = ET.fromstring(res.content)
    news_list = []
    for item in root.findall(".//item")[:count]:
        title = item.findtext("title", default="")
        # 구글뉴스 제목 끝에 " - 언론사명" 이 붙어있어 분리
        source = ""
        if " - " in title:
            title, source = title.rsplit(" - ", 1)
        pub_date = item.findtext("pubDate", default="")
        news_list.append({"title": title, "date": pub_date[:16], "office": source})
    return news_list


if __name__ == "__main__":
    test_code = "442580"
    print("== 현재가 ==")
    print(get_current_price(test_code))
    print("== 뉴스 ==")
    for n in get_news("PLUS 글로벌HBM반도체"):
        print(n)
