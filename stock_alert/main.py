# -*- coding: utf-8 -*-
"""
매일 아침 실행할 메인 스크립트.
1. config.py 의 보유종목 각각 현재가 조회
2. 평가금액 / 비중 계산
3. HTML 리포트 생성 (portfolio_report.html)
4. kakao_token.json 이 있으면 카카오톡 '나에게 보내기'로 요약 발송

실행: python main.py
"""

import os
import json
from datetime import datetime

from fetch_data import get_current_price, get_news

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_holdings():
    """GitHub Actions에서는 HOLDINGS_JSON 시크릿(환경변수)을 우선 사용하고,
    로컬 PC에서는 config.py 의 HOLDINGS를 사용합니다."""
    env_json = os.environ.get("HOLDINGS_JSON")
    if env_json:
        return json.loads(env_json)
    from config import HOLDINGS  # 로컬 전용 (GitHub에는 올라가지 않음)
    return HOLDINGS


def load_kakao_key():
    env_key = os.environ.get("KAKAO_REST_API_KEY")
    if env_key:
        return env_key
    try:
        from config import KAKAO_REST_API_KEY
        return KAKAO_REST_API_KEY
    except ImportError:
        return None


def build_portfolio(holdings):
    rows = []
    total_value = 0
    for h in holdings:
        try:
            price_info = get_current_price(h["code"])
            current_price = price_info["price"]
        except Exception as e:
            print(f"[경고] {h['name']} 시세 조회 실패, 매입가로 대체: {e}")
            current_price = h["avg_price"]
        value = current_price * h["qty"]
        total_value += value
        rows.append({**h, "current_price": current_price, "value": value})

    for r in rows:
        r["weight"] = (r["value"] / total_value * 100) if total_value else 0

    return rows, total_value


def build_html(rows, total_value) -> str:
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows_html = ""

    for r in rows:
        profit_rate = (r["current_price"] - r["avg_price"]) / r["avg_price"] * 100
        color = "#d64545" if profit_rate >= 0 else "#3b6fd6"

        news_html = ""
        try:
            for n in get_news(r["code"], count=2):
                news_html += f'<div class="news-item">· {n["title"]} <span class="news-date">({n["date"]})</span></div>'
        except Exception:
            news_html = '<div class="news-item">뉴스 조회 실패</div>'

        rows_html += f"""
        <tr>
          <td>{r['name']}<div class="code">{r['code']}</div></td>
          <td class="num">{r['qty']:,}</td>
          <td class="num">{r['current_price']:,}원</td>
          <td class="num" style="color:{color}">{profit_rate:+.2f}%</td>
          <td class="num">{r['value']:,}원</td>
          <td class="num">{r['weight']:.1f}%</td>
          <td class="news">{news_html}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>연금저축계좌 포트폴리오 리포트</title>
<style>
  body {{ font-family: -apple-system, 'Malgun Gothic', sans-serif; background:#f5f6f8; margin:0; padding:24px; color:#1a1a1a; }}
  .header h1 {{ font-size:20px; margin:0 0 4px; }}
  .header .date {{ color:#888; font-size:13px; margin-bottom:20px; }}
  .summary {{ background:#fff; border-radius:12px; padding:20px; margin:16px 0 20px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  .summary .total {{ font-size:28px; font-weight:700; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  th, td {{ padding:12px 14px; text-align:left; border-bottom:1px solid #eee; font-size:13px; vertical-align:top; }}
  th {{ background:#fafafa; color:#666; font-weight:600; }}
  .num {{ text-align:right; font-variant-numeric: tabular-nums; }}
  .code {{ color:#999; font-size:11px; }}
  .news-item {{ font-size:11px; color:#555; margin-bottom:2px; }}
  .news-date {{ color:#aaa; }}
</style>
</head>
<body>
  <div class="header">
    <h1>연금저축계좌 포트폴리오 리포트</h1>
    <div class="date">{today} 기준</div>
  </div>
  <div class="summary">
    <div>총 평가금액</div>
    <div class="total">{total_value:,}원</div>
  </div>
  <table>
    <thead>
      <tr>
        <th>종목</th><th class="num">수량</th><th class="num">현재가</th>
        <th class="num">수익률</th><th class="num">평가금액</th><th class="num">비중</th><th>관련 뉴스</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</body>
</html>"""
    return html


def build_kakao_text(rows, total_value) -> str:
    lines = [f"📊 연금저축 포트폴리오 ({datetime.now().strftime('%m/%d')})",
              f"총 평가금액: {total_value:,}원", ""]
    for r in rows:
        profit_rate = (r["current_price"] - r["avg_price"]) / r["avg_price"] * 100
        lines.append(f"{r['name']}: {r['current_price']:,}원 ({profit_rate:+.1f}%) 비중 {r['weight']:.1f}%")
    return "\n".join(lines)


def main():
    holdings = load_holdings()
    kakao_key = load_kakao_key()

    rows, total_value = build_portfolio(holdings)

    html = build_html(rows, total_value)

    docs_dir = os.path.join(BASE_DIR, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    html_path = os.path.join(docs_dir, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML 저장 완료: {html_path}")

    token_path = os.path.join(BASE_DIR, "kakao_token.json")
    if os.path.exists(token_path) and kakao_key:
        from kakao_send import send_to_me
        text = build_kakao_text(rows, total_value)
        try:
            send_to_me(kakao_key, text)
            print("카카오톡 전송 완료")
        except Exception as e:
            print(f"[경고] 카카오톡 전송 실패: {e}")
    else:
        print("kakao_token.json 이 없어 카카오톡 전송은 건너뜁니다.")
        print("먼저 'python kakao_auth.py' 를 실행해서 토큰을 발급하세요.")


if __name__ == "__main__":
    main()
