name: Ntfy Briefing (US stocks)

on:
  schedule:
    # UTC 22:00(월~금) = 한국시간(KST) 다음날 07:00(화~토)
    - cron: '0 22 * * 1-5'
  workflow_dispatch: {}

defaults:
  run:
    working-directory: stock_alert

jobs:
  send-ntfy-us:
    runs-on: ubuntu-latest
    steps:
      - name: 저장소 체크아웃
        uses: actions/checkout@v4

      - name: 파이썬 설치
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: 패키지 설치
        run: pip install -r requirements.txt

      - name: 미국주식 ntfy 발송
        env:
          HOLDINGS_JSON: ${{ secrets.HOLDINGS_JSON }}
          CASH_JSON: ${{ secrets.CASH_JSON }}
          NTFY_TOPIC: ${{ secrets.NTFY_TOPIC }}
        run: python main.py --skip-html --send-ntfy us
