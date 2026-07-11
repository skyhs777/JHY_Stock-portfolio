# -*- coding: utf-8 -*-
"""
시세 조회: 국내는 pykrx 우선(실패 시 네이버 폴백), 미국은 yfinance 우선
(실패 시 Yahoo chart API -> Stooq 순으로 폴백).
뉴스: 구글 뉴스 RSS에서 최근 1일 이내 기사만 필터링해서 가져온다.
"""

import re
import datetime
import requests
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def _to_number(value):
    """'354,000' 같은 콤마 포함 문자열/숫자를 float으로 변환"""
    if isinstance(value, (int, float)):
        return float(value)
    return float(str(value).replace(",", ""))


def _get_current_price_naver(code: str) -> dict:
    """네이버 실시간 시세 (pykrx 실패 시 폴백)"""
    url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{code}"
    res = requests.get(url, headers=HEADERS, timeout=5)
    res.raise_for_status()
    data = res.json()
    item = data["datas"][0] if "datas" in data else data["result"]["areas"][0]["datas"][0]
    return {
        "price": int(_to_number(item["closePrice"])),
        "change": int(_to_number(item["compareToPreviousClosePrice"])),
        "change_rate": _to_number(item["fluctuationsRatio"]),
    }


def get_current_price(code: str) -> dict:
    """국내 종목/ETF/ETN 현재가(직전 종가) 조회. pykrx 우선, 실패 시 네이버로 폴백."""
    try:
        from pykrx import stock
        today = datetime.datetime.now()
        start = (today - datetime.timedelta(days=12)).strftime("%Y%m%d")
        end = today.strftime("%Y%m%d")

        df = stock.get_market_ohlcv_by_date(start, end, code)
        if df is None or df.empty:
            df = stock.get_etf_ohlcv_by_date(start, end, code)

        if df is None or df.empty:
            raise RuntimeError("pykrx: 데이터 없음")

        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        price = int(last["종가"])
        prev_close = int(prev["종가"])
        change = price - prev_close
        change_rate = (change / prev_close * 100) if prev_close else 0.0
        return {"price": price, "change": change, "change_rate": change_rate}
    except Exception as pykrx_err:
        try:
            return _get_current_price_naver(code)
        except Exception as naver_err:
            raise RuntimeError(
                f"국내 시세 조회 실패 (pykrx: {pykrx_err}, naver: {naver_err})"
            )


def get_us_price(ticker: str) -> float:
    """미국 상장 주식 현재가(USD) 조회. yfinance 우선, 실패 시 Yahoo chart -> Stooq 순 폴백."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        price = t.fast_info.get("lastPrice") or t.fast_info.get("last_price")
        if price is None:
            hist = t.history(period="1d")
            price = float(hist["Close"].iloc[-1])
        return float(price)
    except Exception as yf_err:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            res = requests.get(url, headers=HEADERS, timeout=5)
            res.raise_for_status()
            data = res.json()
            return float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])
        except Exception as yahoo_err:
            try:
                url = f"https://stooq.com/q/l/?s={ticker.lower()}.us&f=sd2t2ohlcv&h&e=csv"
                res = requests.get(url, headers=HEADERS, timeout=5)
                res.raise_for_status()
                line = res.text.strip().split("\n")[1]
                close = line.split(",")[6]
                return float(close)
            except Exception as stooq_err:
                raise RuntimeError(
                    f"미국주식 시세 조회 실패 (yfinance: {yf_err}, yahoo: {yahoo_err}, stooq: {stooq_err})"
                )


def get_usd_krw_rate() -> float:
    """실시간에 가까운 원달러 환율 조회. yfinance 우선, 실패 시 Yahoo -> Frankfurter(ECB) 순 폴백."""
    try:
        import yfinance as yf
        t = yf.Ticker("KRW=X")
        price = t.fast_info.get("lastPrice") or t.fast_info.get("last_price")
        if price is None:
            hist = t.history(period="1d")
            price = float(hist["Close"].iloc[-1])
        return float(price)
    except Exception as yf_err:
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/KRW=X"
            res = requests.get(url, headers=HEADERS, timeout=5)
            res.raise_for_status()
            data = res.json()
            return float(data["chart"]["result"][0]["meta"]["regularMarketPrice"])
        except Exception as yahoo_err:
            try:
                url = "https://api.frankfurter.dev/v1/latest?from=USD&to=KRW"
                res = requests.get(url, headers=HEADERS, timeout=5)
                res.raise_for_status()
                return float(res.json()["rates"]["KRW"])
            except Exception as fx_err:
                raise RuntimeError(
                    f"환율 조회 실패 (yfinance: {yf_err}, yahoo: {yahoo_err}, frankfurter: {fx_err})"
                )


def get_news(name: str, count: int = 2, max_age_hours: int = 24) -> list:
    """구글 뉴스 RSS로 종목명 관련 최신 뉴스 조회. max_age_hours 이내(기본 24시간=1일) 기사만 반환."""
    query = quote(f"{name}")
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    res = requests.get(url, headers=HEADERS, timeout=5)
    res.raise_for_status()

    root = ET.fromstring(res.content)
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(hours=max_age_hours)

    news_list = []
    for item in root.findall(".//item"):
        title = item.findtext("title", default="")
        source = ""
        if " - " in title:
            title, source = title.rsplit(" - ", 1)
        pub_date_raw = item.findtext("pubDate", default="")
        try:
            pub_dt = parsedate_to_datetime(pub_date_raw)
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=datetime.timezone.utc)
        except Exception:
            continue
        if pub_dt < cutoff:
            continue
        news_list.append({"title": title, "date": pub_dt.strftime("%m/%d %H:%M"), "office": source})
        if len(news_list) >= count:
            break
    return news_list


if __name__ == "__main__":
    print("== 국내 시세(005930) ==")
    print(get_current_price("005930"))
    print("== 미국주식(NVDA) ==")
    print(get_us_price("NVDA"))
    print("== 환율 ==")
    print(get_usd_krw_rate())
    print("== 뉴스(1일 이내) ==")
    for n in get_news("삼성전자"):
        print(n)
