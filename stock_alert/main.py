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

from fetch_data import get_current_price, get_news, get_us_price, get_usd_krw_rate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_holdings():
    """GitHub Actions에서는 HOLDINGS_JSON 시크릿(환경변수)을 우선 사용하고,
    로컬 PC에서는 config.py 의 HOLDINGS를 사용합니다."""
    env_json = os.environ.get("HOLDINGS_JSON")
    if env_json:
        return json.loads(env_json)
    from config import HOLDINGS  # 로컬 전용 (GitHub에는 올라가지 않음)
    return HOLDINGS


def load_cash():
    """예수금(현금) 목록. 형식: [{"account":"연금저축","amount":500000}, ...]
    CASH_JSON 시크릿이 없으면 빈 리스트."""
    env_json = os.environ.get("CASH_JSON")
    if env_json:
        return json.loads(env_json)
    try:
        from config import CASH
        return CASH
    except ImportError:
        return []


def load_kakao_key():
    env_key = os.environ.get("KAKAO_REST_API_KEY")
    if env_key:
        return env_key
    try:
        from config import KAKAO_REST_API_KEY
        return KAKAO_REST_API_KEY
    except ImportError:
        return None


def build_portfolio(holdings, cash_list=None):
    cash_list = cash_list or []
    rows = []
    total_value = 0
    fx_now = None  # 원달러 환율은 한 번만 조회해서 재사용

    for h in holdings:
        fetch_failed = False
        currency = h.get("currency", "KRW")

        if currency == "USD":
            try:
                price_fc = get_us_price(h["code"])
                if fx_now is None:
                    fx_now = get_usd_krw_rate()
            except Exception as e:
                print(f"[경고] {h['name']} 미국주식 시세/환율 조회 실패, 매입가로 대체: {e}")
                price_fc = h["avg_price"]
                fx_now = fx_now or h.get("purchase_fx", 1)
                fetch_failed = True
            current_price_display = price_fc
            current_price_krw = price_fc * fx_now
            avg_price_krw = h["avg_price"] * h.get("purchase_fx", fx_now)
        else:
            try:
                price_info = get_current_price(h["code"])
                current_price_display = price_info["price"]
            except Exception as e:
                print(f"[경고] {h['name']} 시세 조회 실패, 매입가로 대체: {e}")
                current_price_display = h["avg_price"]
                fetch_failed = True
            current_price_krw = current_price_display
            avg_price_krw = h["avg_price"]

        value = current_price_krw * h["qty"]
        total_value += value
        rows.append({
            **h,
            "account": h.get("account", "연금저축"),
            "sector": h.get("sector", "미분류"),
            "asset_type": h.get("asset_type", "위험자산"),
            "currency": currency,
            "current_price": current_price_display,
            "current_price_krw": current_price_krw,
            "avg_price_krw": avg_price_krw,
            "fx_now": fx_now if currency == "USD" else None,
            "value": value,
            "fetch_failed": fetch_failed,
            "is_cash": False,
        })

    # 예수금은 시세 조회 없이 그대로 평가금액에 반영되는 가상의 종목으로 취급
    for c in cash_list:
        value = c["amount"]
        total_value += value
        rows.append({
            "name": "예수금",
            "code": "-",
            "qty": 1,
            "avg_price": value,
            "avg_price_krw": value,
            "current_price": value,
            "current_price_krw": value,
            "currency": "KRW",
            "fx_now": None,
            "account": c.get("account", "연금저축"),
            "sector": "예수금",
            "asset_type": "예수금",
            "value": value,
            "fetch_failed": False,
            "is_cash": True,
        })

    for r in rows:
        r["weight"] = (r["value"] / total_value * 100) if total_value else 0

    return rows, total_value


PALETTE = ["#4f7cff", "#ff7a5c", "#3ecf8e", "#f5c542", "#9b6bff", "#3ac2c2", "#ff5c93"]


def build_pie_chart(rows) -> str:
    """순수 SVG로 만드는 비중 도넛차트 (외부 라이브러리 불필요).
    전달된 rows들만의 합계를 100%로 다시 계산한다 (계좌별 탭에서 그 계좌만의 비중이 되도록)."""
    local_total = sum(row["value"] for row in rows) or 1
    size = 220
    r = 80
    stroke = 34
    cx = cy = size / 2
    circumference = 2 * 3.14159265 * r

    segments_svg = ""
    cumulative = 0
    for i, row in enumerate(rows):
        local_weight = row["value"] / local_total * 100
        color = PALETTE[i % len(PALETTE)]
        dash = (local_weight / 100) * circumference
        gap = max(circumference - dash, 0)
        offset = -cumulative
        segments_svg += (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-dasharray="{dash:.2f} {gap:.2f}" '
            f'stroke-dashoffset="{offset:.2f}" transform="rotate(-90 {cx} {cy})" />'
        )
        cumulative += dash

    legend_html = ""
    for i, row in enumerate(rows):
        local_weight = row["value"] / local_total * 100
        color = PALETTE[i % len(PALETTE)]
        legend_html += (
            f'<div class="legend-item">'
            f'<span class="legend-dot" style="background:{color}"></span>'
            f'{row["name"]} <b>{local_weight:.1f}%</b>'
            f'</div>'
        )

    svg = f"""
    <svg viewBox="0 0 {size} {size}" width="220" height="220">
      {segments_svg}
    </svg>"""

    return f"""
    <div class="pie-wrap">
      {svg}
      <div class="legend">{legend_html}</div>
    </div>"""


def build_sector_chart(rows) -> str:
    """종목의 sector 필드로 그룹핑해서 섹터별 비중 도넛차트를 만든다."""
    sector_values = {}
    for row in rows:
        sector_values[row["sector"]] = sector_values.get(row["sector"], 0) + row["value"]
    total = sum(sector_values.values()) or 1

    size = 220
    r = 80
    stroke = 34
    cx = cy = size / 2
    circumference = 2 * 3.14159265 * r

    segments_svg = ""
    legend_html = ""
    cumulative = 0
    for i, (sector, value) in enumerate(sector_values.items()):
        weight = value / total * 100
        color = PALETTE[i % len(PALETTE)]
        dash = (weight / 100) * circumference
        gap = circumference - dash
        offset = -cumulative
        segments_svg += (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-dasharray="{dash:.2f} {gap:.2f}" '
            f'stroke-dashoffset="{offset:.2f}" transform="rotate(-90 {cx} {cy})" />'
        )
        cumulative += dash
        legend_html += (
            f'<div class="legend-item">'
            f'<span class="legend-dot" style="background:{color}"></span>'
            f'{sector} <b>{weight:.1f}%</b>'
            f'</div>'
        )

    svg = f"""
    <svg viewBox="0 0 {size} {size}" width="220" height="220">
      {segments_svg}
    </svg>"""

    return f"""
    <div class="pie-wrap">
      {svg}
      <div class="legend">{legend_html}</div>
    </div>"""


def build_asset_type_chart(rows, account: str) -> str:
    """특정 계좌(예: IRP)만 필터링해서 위험자산/안전자산 비중 도넛차트를 만든다."""
    filtered = [r for r in rows if r["account"] == account]
    if not filtered:
        return ""

    type_values = {}
    for row in filtered:
        type_values[row["asset_type"]] = type_values.get(row["asset_type"], 0) + row["value"]
    total = sum(type_values.values()) or 1

    size = 220
    r = 80
    stroke = 34
    cx = cy = size / 2
    circumference = 2 * 3.14159265 * r

    type_colors = {"위험자산": "#ff7a5c", "안전자산": "#4f7cff", "예수금": "#3ecf8e"}

    segments_svg = ""
    legend_html = ""
    cumulative = 0
    for i, (t, value) in enumerate(type_values.items()):
        weight = value / total * 100
        color = type_colors.get(t, PALETTE[i % len(PALETTE)])
        dash = (weight / 100) * circumference
        gap = circumference - dash
        offset = -cumulative
        segments_svg += (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-dasharray="{dash:.2f} {gap:.2f}" '
            f'stroke-dashoffset="{offset:.2f}" transform="rotate(-90 {cx} {cy})" />'
        )
        cumulative += dash
        legend_html += (
            f'<div class="legend-item">'
            f'<span class="legend-dot" style="background:{color}"></span>'
            f'{t} <b>{weight:.1f}%</b>'
            f'</div>'
        )

    svg = f"""
    <svg viewBox="0 0 {size} {size}" width="220" height="220">
      {segments_svg}
    </svg>"""

    return f"""
    <div class="section-title">{account} 위험자산/안전자산 비중</div>
    <div class="pie-wrap">
      {svg}
      <div class="legend">{legend_html}</div>
    </div>"""


def build_account_weight_chart(rows) -> str:
    """전체 자산을 계좌 기준으로 그룹핑해서 비중 도넛차트를 만든다 (개요 탭용)."""
    account_values = {}
    for row in rows:
        account_values[row["account"]] = account_values.get(row["account"], 0) + row["value"]
    total = sum(account_values.values()) or 1

    size = 220
    r = 80
    stroke = 34
    cx = cy = size / 2
    circumference = 2 * 3.14159265 * r

    segments_svg = ""
    legend_html = ""
    cumulative = 0
    for i, (acc, value) in enumerate(account_values.items()):
        weight = value / total * 100
        color = PALETTE[i % len(PALETTE)]
        dash = (weight / 100) * circumference
        gap = circumference - dash
        offset = -cumulative
        segments_svg += (
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-dasharray="{dash:.2f} {gap:.2f}" '
            f'stroke-dashoffset="{offset:.2f}" transform="rotate(-90 {cx} {cy})" />'
        )
        cumulative += dash
        legend_html += (
            f'<div class="legend-item">'
            f'<span class="legend-dot" style="background:{color}"></span>'
            f'{acc} <b>{weight:.1f}%</b> ({value:,.0f}원)'
            f'</div>'
        )

    svg = f"""
    <svg viewBox="0 0 {size} {size}" width="220" height="220">
      {segments_svg}
    </svg>"""

    return f"""
    <div class="pie-wrap">
      {svg}
      <div class="legend">{legend_html}</div>
    </div>"""


def render_rows_html(rows) -> str:
    """종목 테이블의 <tr> 목록 HTML을 만든다. 계좌별 탭, 전체 탭 어디서나 재사용.
    비중(%)은 전달된 rows들만의 합계를 100%로 다시 계산한다."""
    local_total = sum(row["value"] for row in rows) or 1
    rows_html = ""
    for r in rows:
        local_weight = r["value"] / local_total * 100
        if r.get("is_cash"):
            rows_html += f"""
        <tr class="cash-row">
          <td class="account-tag">{r['account']}</td>
          <td>{r['name']}<div class="code">현금성자산</div></td>
          <td class="num">-</td>
          <td class="num">-</td>
          <td class="num">{r['current_price']:,}원</td>
          <td class="num">-</td>
          <td class="num">{r['value']:,}원</td>
          <td class="num">{local_weight:.1f}%</td>
          <td class="news">-</td>
        </tr>"""
            continue

        profit_rate = (r["current_price_krw"] - r["avg_price_krw"]) / r["avg_price_krw"] * 100
        color = "#d64545" if profit_rate >= 0 else "#3b6fd6"
        arrow = "▲" if profit_rate >= 0 else "▼"
        warn = ' <span class="warn" title="시세 조회 실패, 매입가로 대체됨">⚠</span>' if r.get("fetch_failed") else ""

        if r["currency"] == "USD":
            avg_price_disp = f"${r['avg_price']:,.2f}"
            current_price_disp = f"${r['current_price']:,.2f} <span class=\"fx-note\">(₩{r['current_price_krw']:,.0f})</span>"
        else:
            avg_price_disp = f"{r['avg_price']:,}원"
            current_price_disp = f"{r['current_price']:,}원"

        news_html = ""
        try:
            for n in get_news_cached(r["name"], count=2):
                news_html += f'<div class="news-item">· {n["title"]} <span class="news-date">({n["date"]})</span></div>'
        except Exception:
            news_html = '<div class="news-item">뉴스 조회 실패</div>'
        if not news_html:
            news_html = '<div class="news-item">최근 1일 이내 뉴스 없음</div>'

        rows_html += f"""
        <tr>
          <td class="account-tag">{r['account']}</td>
          <td>{r['name']}<div class="code">{r['code']}</div></td>
          <td class="num">{r['qty']:,}</td>
          <td class="num">{avg_price_disp}</td>
          <td class="num">{current_price_disp}{warn}</td>
          <td class="num" style="color:{color}"><b>{arrow} {profit_rate:+.2f}%</b></td>
          <td class="num">{r['value']:,.0f}원</td>
          <td class="num">{local_weight:.1f}%</td>
          <td class="news">{news_html}</td>
        </tr>"""
    return rows_html


TABLE_HEAD = """
    <tr>
      <th>계좌</th><th>종목</th><th class="num">수량</th><th class="num">매입가</th><th class="num">현재가</th>
      <th class="num">수익률</th><th class="num">평가금액</th><th class="num">비중</th><th>관련 뉴스</th>
    </tr>"""


def render_account_section(account: str, rows_all) -> str:
    """탭 하나(계좌 하나)에 들어갈 전체 콘텐츠(요약/차트/표)를 만든다."""
    subset = [r for r in rows_all if r["account"] == account]
    account_total = sum(r["value"] for r in subset)

    pie_html = build_pie_chart(subset)
    sector_html = build_sector_chart(subset)
    asset_type_html = build_asset_type_chart(rows_all, account) if account == "IRP" else ""
    rows_html = render_rows_html(subset)

    return f"""
    <div class="summary">
      <div>{account} 평가금액</div>
      <div class="total">{account_total:,.0f}원</div>
    </div>

    <div class="section-title">종목별 비중</div>
    {pie_html}

    <div class="section-title">섹터별 비중</div>
    {sector_html}

    {asset_type_html}

    <table>
      <thead>{TABLE_HEAD}</thead>
      <tbody>{rows_html}</tbody>
    </table>"""


_NEWS_CACHE = {}


def get_news_cached(name: str, count: int = 2):
    """같은 실행 중에는 종목당 뉴스 조회를 한 번만 하도록 캐싱."""
    key = (name, count)
    if key not in _NEWS_CACHE:
        try:
            _NEWS_CACHE[key] = get_news(name, count=count)
        except Exception:
            _NEWS_CACHE[key] = []
    return _NEWS_CACHE[key]


def build_daily_briefing(rows, total_value, include_news=True) -> str:
    """카카오톡/웹페이지 공용 일일 브리핑 텍스트.
    계좌별로 종목의 오늘 종가·등락률과 (선택) 최근 1일 이내 뉴스를 정리한다."""
    today = datetime.now().strftime("%m/%d")
    lines = [f"📊 포트폴리오 브리핑 ({today})", f"총 평가금액: {total_value:,.0f}원", ""]

    accounts_order = []
    for r in rows:
        if r["account"] not in accounts_order:
            accounts_order.append(r["account"])

    for acc in accounts_order:
        subset = [r for r in rows if r["account"] == acc and not r.get("is_cash")]
        if not subset:
            continue
        acc_total = sum(r["value"] for r in rows if r["account"] == acc)
        lines.append(f"[{acc}] {acc_total:,.0f}원")
        for r in subset:
            profit_rate = (r["current_price_krw"] - r["avg_price_krw"]) / r["avg_price_krw"] * 100
            if r["currency"] == "USD":
                price_str = f"${r['current_price']:,.2f}(₩{r['current_price_krw']:,.0f})"
            else:
                price_str = f"{r['current_price']:,}원"
            lines.append(f"· {r['name']} {price_str} ({profit_rate:+.1f}%)")
            if include_news:
                for n in get_news_cached(r["name"], count=1):
                    lines.append(f"   📰 {n['title']} ({n['date']})")
        lines.append("")

    return "\n".join(lines).strip()


def build_html(rows, total_value) -> str:
    today = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 계좌 목록 (등장 순서 유지, 선호 순서: 연금저축 -> IRP -> CMA -> 그 외)
    preferred_order = ["연금저축", "IRP", "CMA"]
    seen_accounts = []
    for r in rows:
        if r["account"] not in seen_accounts:
            seen_accounts.append(r["account"])
    accounts = [a for a in preferred_order if a in seen_accounts] + \
               [a for a in seen_accounts if a not in preferred_order]

    # 계좌별 소계 카드 (개요 탭)
    account_totals = {}
    for r in rows:
        account_totals[r["account"]] = account_totals.get(r["account"], 0) + r["value"]

    account_cards_html = ""
    for acc in accounts:
        account_cards_html += f"""
        <div class="account-card">
          <div class="account-name">{acc}</div>
          <div class="account-value">{account_totals[acc]:,.0f}원</div>
        </div>"""

    account_weight_chart_html = build_account_weight_chart(rows) if len(accounts) > 1 else ""

    # 탭 버튼 (개요 + 계좌별)
    tab_buttons_html = '<button class="tab-btn active" onclick="showTab(\'overview\', this)">개요</button>'
    for acc in accounts:
        tab_buttons_html += f'<button class="tab-btn" onclick="showTab(\'acc_{acc}\', this)">{acc}</button>'

    # 개요 탭 콘텐츠
    overview_html = f"""
    <div class="summary">
      <div>총 평가금액 (예수금 포함)</div>
      <div class="total">{total_value:,.0f}원</div>
    </div>
    <div class="account-cards">{account_cards_html}</div>
    {'<div class="section-title">계좌별 비중</div>' if account_weight_chart_html else ''}
    {account_weight_chart_html}
    """

    # 계좌별 탭 콘텐츠
    account_tabs_html = ""
    for acc in accounts:
        account_tabs_html += f"""
    <div id="acc_{acc}" class="tab-content" style="display:none">
      {render_account_section(acc, rows)}
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>포트폴리오 리포트</title>
<style>
  body {{ font-family: -apple-system, 'Malgun Gothic', sans-serif; background:#f5f6f8; margin:0; padding:24px; color:#1a1a1a; }}
  .header h1 {{ font-size:20px; margin:0 0 4px; }}
  .header .date {{ color:#888; font-size:13px; margin-bottom:16px; }}
  .tab-bar {{ display:flex; gap:8px; margin-bottom:20px; flex-wrap:wrap; }}
  .tab-btn {{ border:none; background:#e8e9ec; color:#555; padding:10px 18px; border-radius:999px; font-size:14px; font-weight:600; cursor:pointer; }}
  .tab-btn.active {{ background:#1a1a1a; color:#fff; }}
  .tab-content {{ display:block; }}
  .summary {{ background:#fff; border-radius:12px; padding:20px; margin:0 0 20px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  .summary .total {{ font-size:28px; font-weight:700; }}
  .pie-wrap {{ display:flex; align-items:center; gap:24px; flex-wrap:wrap; background:#fff; border-radius:12px; padding:20px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  .legend {{ flex:1; min-width:180px; }}
  .legend-item {{ font-size:13px; margin-bottom:8px; display:flex; align-items:center; gap:8px; }}
  .legend-dot {{ width:10px; height:10px; border-radius:50%; display:inline-block; flex-shrink:0; }}
  table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  th, td {{ padding:12px 14px; text-align:left; border-bottom:1px solid #eee; font-size:13px; vertical-align:top; }}
  th {{ background:#fafafa; color:#666; font-weight:600; }}
  .num {{ text-align:right; font-variant-numeric: tabular-nums; }}
  .code {{ color:#999; font-size:11px; }}
  .news-item {{ font-size:11px; color:#555; margin-bottom:2px; }}
  .news-date {{ color:#aaa; }}
  .warn {{ color:#e0a300; cursor:help; }}
  .account-tag {{ color:#666; font-size:11px; white-space:nowrap; }}
  .account-cards {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:20px; }}
  .account-card {{ background:#fff; border-radius:12px; padding:16px 20px; box-shadow:0 1px 3px rgba(0,0,0,0.08); flex:1; min-width:140px; }}
  .account-card .account-name {{ color:#888; font-size:12px; margin-bottom:4px; }}
  .account-card .account-value {{ font-size:18px; font-weight:700; }}
  .section-title {{ font-size:14px; font-weight:600; color:#555; margin:0 0 8px 4px; }}
  .cash-row td {{ color:#888; font-style:italic; }}
  .fx-note {{ color:#999; font-size:11px; font-weight:normal; }}
</style>
</head>
<body>
  <div class="header">
    <h1>포트폴리오 리포트</h1>
    <div class="date">{today} 기준</div>
  </div>

  <div class="tab-bar">{tab_buttons_html}</div>

  <div id="overview" class="tab-content">
    {overview_html}
  </div>
  {account_tabs_html}

  <script>
    function showTab(id, btn) {{
      document.querySelectorAll('.tab-content').forEach(function(el) {{ el.style.display = 'none'; }});
      document.getElementById(id).style.display = 'block';
      document.querySelectorAll('.tab-btn').forEach(function(b) {{ b.classList.remove('active'); }});
      if (btn) btn.classList.add('active');
    }}
  </script>
</body>
</html>"""
    return html


def build_kakao_text(rows_subset, total_value) -> str:
    text = build_daily_briefing(rows_subset, total_value, include_news=True)
    if len(text) > 900:
        # 카카오 메시지 길이 제한을 넘으면 뉴스는 빼고 가격만 남긴다
        text = build_daily_briefing(rows_subset, total_value, include_news=False)
        text += "\n(뉴스는 웹페이지에서 확인해주세요 - 메시지 길이 제한)"
    return text


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-html", action="store_true", help="HTML 리포트 생성을 건너뜀")
    parser.add_argument(
        "--send-kakao", choices=["none", "kr", "us", "all"], default="none",
        help="카카오톡 발송 대상: none(안 보냄), kr(한국주식만), us(미국주식만), all(전체)"
    )
    args = parser.parse_args()

    holdings = load_holdings()
    cash_list = load_cash()
    kakao_key = load_kakao_key()

    rows, total_value = build_portfolio(holdings, cash_list)

    if not args.skip_html:
        html = build_html(rows, total_value)
        docs_dir = os.path.join(BASE_DIR, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        html_path = os.path.join(docs_dir, "index.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML 저장 완료: {html_path}")
    else:
        print("--skip-html 옵션으로 HTML 생성은 건너뜀")

    if args.send_kakao == "none":
        print("--send-kakao 옵션이 없어 카카오톡은 보내지 않음")
        return

    if args.send_kakao == "kr":
        subset = [r for r in rows if r["currency"] == "KRW"]
    elif args.send_kakao == "us":
        subset = [r for r in rows if r["currency"] == "USD"]
    else:
        subset = rows
    subset_total = sum(r["value"] for r in subset)

    token_path = os.path.join(BASE_DIR, "kakao_token.json")
    if os.path.exists(token_path) and kakao_key:
        from kakao_send import send_to_me
        text = build_kakao_text(subset, subset_total)
        try:
            send_to_me(kakao_key, text)
            print(f"카카오톡 전송 완료 ({args.send_kakao})")
        except Exception as e:
            print(f"[경고] 카카오톡 전송 실패: {e}")
    else:
        print("kakao_token.json 이 없어 카카오톡 전송은 건너뜁니다.")
        print("먼저 'python kakao_auth.py' 를 실행해서 토큰을 발급하세요.")


if __name__ == "__main__":
    main()
