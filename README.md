# 성구 텔레그램 봇

구글 시트에 있는 성구를 매일 정해진 시간(기본 06:00 KST)에 텔레그램 그룹으로 순서대로 전송합니다.

- 구글 시트: `순서 / 성구 / 성구 제목 / 성구 내용` 열 중 **성구 제목**, **성구 내용** 열을 사용합니다.
- **생명의 어록** 열(E열)에 내용이 있으면, 같은 행의 성구 아래에 이어서 함께 전송합니다. 비어 있으면 성구만 보냅니다.
- 위에서부터 순서대로 하루 한 줄씩 보내고, 끝까지 가면 처음부터 다시 순환합니다.

이 프로젝트에는 두 가지 실행 방식이 있습니다. **하나만 선택해서 사용하세요** (둘 다 켜두면 중복 전송됩니다).

## 방식 A. GitHub Actions (PC를 꺼둬도 동작, 추천)

`send_verse_scheduled.py` + `.github/workflows/daily-verse.yml` 사용.

### 설정 방법
1. GitHub에서 새 저장소를 만듭니다 (Private 권장).
2. 이 폴더를 그 저장소에 푸시합니다.
3. 저장소 **Settings → Secrets and variables → Actions → New repository secret** 에서 아래 4개를 등록합니다.
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID` (여러 그룹에 보내려면 쉼표로 구분: `-1001111111111,-1002222222222`)
   - `GOOGLE_SHEET_ID`
   - `GOOGLE_SHEET_GID`
4. **Actions** 탭에서 "Send daily verse" 워크플로우를 확인합니다. 우측 상단 **Run workflow** 버튼으로 즉시 테스트 실행이 가능합니다.
5. 시작 기준일은 `send_verse_scheduled.py`의 `START_DATE`(기본 2026-09-15)로 계산합니다. 필요하면 워크플로우 env에 `START_DATE` 시크릿/변수를 추가해 조정하세요.

### 매일 정확한 시각에 실행되게 하기 (외부 크론 → repository_dispatch)

GitHub의 `schedule` 트리거는 내부 대기열이 붐빌 때 **몇 시간까지도 지연**될 수 있습니다(GitHub 공식 문서에 명시된 한계). 이 워크플로우는 그래서 `schedule` 대신 `repository_dispatch` 이벤트로 실행되도록 되어 있고, 외부의 정확한 무료 크론 서비스가 매일 정해진 시각에 GitHub API를 호출해 이 이벤트를 쏴줍니다. `workflow_dispatch`/`repository_dispatch`는 위 대기열을 타지 않아 API 호출 즉시(수 초~1분 내) 실행됩니다.

1. **GitHub 개인 액세스 토큰(PAT) 발급**
   - GitHub → 우측 프로필 → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**
   - Repository access: **Only select repositories** → 이 저장소만 선택
   - Permissions → **Actions**: Read and write 로 설정
   - 생성된 토큰 문자열을 안전한 곳에 복사해둡니다 (다시 볼 수 없음)
2. **[cron-job.org](https://cron-job.org)** 등 무료 크론 서비스에 가입 후 새 작업 생성
   - URL: `https://api.github.com/repos/Karion71/bible-verse-bot/dispatches`
   - Method: `POST`
   - Headers:
     - `Authorization: Bearer <위에서 만든 토큰>`
     - `Accept: application/vnd.github+json`
     - `Content-Type: application/json`
   - Body(JSON): `{"event_type": "send-verse"}`
   - 실행 시각: 매일 06:05, 시간대 **Asia/Seoul**
3. 저장 후 "Test run"으로 한 번 호출해보고, GitHub **Actions** 탭에 워크플로우 실행이 즉시 뜨는지 확인합니다.

## 방식 B. 이 PC에서 24시간 프로세스로 실행

`bot.py` (APScheduler로 자체 스케줄링, `state.json`에 다음 순서 기억) 사용.

```bash
pip install -r requirements.txt
python bot.py
```

- 창 없이 백그라운드로 띄우려면 `run_hidden.vbs`를 더블클릭하세요.
- PC 로그인할 때마다 자동 실행되게 하려면 `run_hidden.vbs`의 바로가기를 만들어
  `Win+R` → `shell:startup` 폴더에 넣으세요.
- 이 방식은 **PC가 켜져 있고 로그인되어 있어야만** 동작합니다.

## 테스트 전송

```bash
python test_send.py
```

스케줄과 무관하게 지금 바로 다음 순서 성구 1건을 보내고, `state.json`의 순서를 한 칸 전진시킵니다. (방식 A만 쓸 경우 `test_send.py`/`bot.py`는 실행하지 마세요 — `state.json` 카운터와 `send_verse_scheduled.py`의 날짜 계산이 서로 다른 방식이라 순서가 어긋날 수 있습니다.)

## 파일 구성

| 파일 | 용도 |
|---|---|
| `bot.py` | 방식 B: 상시 구동 프로세스 |
| `send_verse_scheduled.py` | 방식 A: GitHub Actions 등 1회성 실행용 |
| `test_send.py` | 수동 테스트 전송 |
| `.env` | 방식 B용 로컬 설정값 (토큰 등, git에 올리지 않음) |
| `.github/workflows/daily-verse.yml` | 방식 A용 GitHub Actions 예약 실행 정의 |
| `state.json` | 방식 B의 "다음에 보낼 순서" 기록 (git에 올리지 않음) |
