# 스텝바이스텝: GitHub Actions로 매일 자동 갱신되는 포트폴리오 리포트 만들기

PC 없이도 폰으로 항상 최신 리포트를 볼 수 있게 만드는 전체 과정입니다.
지금 빌린 PC로 아래 과정을 한 번만 세팅해두면, 그 뒤로는 PC가 꺼져 있어도
GitHub의 서버가 알아서 실행합니다.

---

## STEP 1. GitHub 계정 만들기

1. https://github.com 접속 → 우측 상단 **Sign up**
2. 이메일 · 비밀번호 · 사용자명 입력 후 계정 생성 (무료)

---

## STEP 2. 새 저장소(repository) 만들기

1. 로그인 후 우측 상단 **+** → **New repository**
2. Repository name: `stock-portfolio-report` (원하는 이름으로 가능)
3. **Public** 선택 (무료 Pages는 Public만 가능 — 이전에 설명드린 부분)
4. **Create repository** 클릭

---

## STEP 3. 파일 업로드

방금 제가 드린 압축 파일 안의 아래 파일들을 그대로 업로드하면 됩니다
(단, `config.py`는 업로드하지 마세요 — 실제 수치가 든 로컬 전용 파일입니다):

```
stock_alert/
├── .github/workflows/update-report.yml
├── .gitignore
├── config.example.py
├── fetch_data.py
├── kakao_auth.py
├── kakao_send.py
├── main.py
├── requirements.txt
└── README.md
```

업로드 방법:
1. 저장소 페이지에서 **Add file → Upload files**
2. 파일들을 통째로 드래그 앤 드롭 (폴더 구조 그대로 유지됨)
   - `.github` 폴더처럼 점(.)으로 시작하는 폴더도 브라우저 업로드로 그대로 올라갑니다
3. 하단 **Commit changes** 클릭

---

## STEP 4. 보유 종목 정보를 Secret으로 등록

실제 종목/수량은 코드에 넣지 않고, GitHub의 비공개 저장 공간인 **Secrets**에 넣습니다.

1. 저장소 상단 **Settings** 탭
2. 왼쪽 메뉴 **Secrets and variables → Actions**
3. **New repository secret** 클릭
4. Name: `HOLDINGS_JSON`
5. Value에 아래 형식으로 한 줄 JSON 입력 (연금저축 7종목 예시):

```json
[{"name":"PLUS 글로벌HBM반도체","code":"442580","qty":246,"avg_price":63075},{"name":"KODEX 미국AI전력핵심인프라","code":"487230","qty":444,"avg_price":19052},{"name":"TIGER 미국필라델피아AI반도체나스닥","code":"497570","qty":433,"avg_price":15938},{"name":"KODEX 미국AI광통신네트워크","code":"0173Y0","qty":256,"avg_price":12627},{"name":"RISE 글로벌원자력","code":"442320","qty":82,"avg_price":24082},{"name":"KODEX 미국우주항공","code":"0167Z0","qty":292,"avg_price":10245},{"name":"SOL 미국AI전력인프라","code":"486450","qty":118,"avg_price":13583}]
```

6. **Add secret** 클릭

---

## STEP 5. (선택) 카카오톡 연동 Secret 등록

카카오톡 알림도 원하시면:

1. 먼저 빌린 PC에서 `python kakao_auth.py`를 로컬로 실행해 `kakao_token.json`을 만드세요
   (사전 준비는 README.md의 "4단계. 카카오톡 연동" 참고)
2. 생성된 `kakao_token.json` 파일 내용을 통째로 복사
3. GitHub Secrets에 두 개 추가:
   - `KAKAO_REST_API_KEY` → 카카오 디벨로퍼스에서 발급받은 REST API 키
   - `KAKAO_TOKEN_JSON` → 방금 복사한 kakao_token.json 파일 내용 전체

카카오톡 없이 HTML 리포트만 원하시면 이 단계는 건너뛰어도 됩니다.

---

## STEP 6. GitHub Pages 활성화

1. **Settings → Pages**
2. Source: **GitHub Actions** 선택 (Deploy from a branch 아님, GitHub Actions 옵션)
3. 저장하면 끝 — 별도 브랜치 설정 불필요 (워크플로 파일이 자동으로 처리)

---

## STEP 7. 수동으로 한 번 실행해서 테스트

1. 저장소 상단 **Actions** 탭
2. 왼쪽에서 **Update Portfolio Report** 워크플로 클릭
3. 우측 **Run workflow** 버튼 클릭 → 다시 **Run workflow**
4. 1~2분 기다리면 초록 체크(✓)로 성공 표시됨. 빨간 X면 로그 열어서 에러 확인
   (에러 나면 그 로그를 저에게 붙여넣어 주시면 같이 고칠 수 있습니다)

---

## STEP 8. 완성된 리포트 URL 확인

1. **Settings → Pages** 상단에 "Your site is live at ..." 형태로 URL이 뜹니다
   (보통 `https://사용자명.github.io/stock-portfolio-report/` 형태)
2. 그 링크를 폰 브라우저로 열어서 확인
3. 폰에서 **홈 화면에 추가** (Safari: 공유 → 홈 화면에 추가 / Chrome: 메뉴 → 홈 화면에 추가)
   해두면 앱 아이콘처럼 원터치로 열립니다

---

## STEP 9. 실행 주기 조정 (선택)

기본값은 "평일 한국시간 9시~16시, 30분마다"입니다. 바꾸고 싶으면
`.github/workflows/update-report.yml` 파일의 `cron` 값을 수정하면 됩니다
(GitHub 웹에서 그 파일 열고 연필 아이콘으로 바로 수정 가능).

---

## 참고: 이후 PC 없이 유지보수하는 법

- 종목이 바뀌면: Settings → Secrets → HOLDINGS_JSON → 값 수정
- 카카오 리프레시 토큰은 보통 두 달 정도 지나면 갱신이 필요할 수 있습니다.
  이땐 PC(또는 Claude Code가 되는 아무 환경)에서 `kakao_auth.py`를 다시 실행해서
  새 `kakao_token.json`으로 `KAKAO_TOKEN_JSON` 시크릿 값만 교체하면 됩니다.
