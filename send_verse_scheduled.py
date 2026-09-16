"""
GitHub Actions 등 '매일 1회 실행 후 종료'되는 환경에서 쓰는 버전.
실행될 때마다 프로세스가 새로 뜨므로(상태 파일을 유지할 수 없으므로),
"기준일로부터 며칠째인지"를 계산해서 그 날짜에 해당하는 성구를 순서대로 보낸다.
목록 끝까지 가면 처음부터 순환한다.
"""

import csv
import io
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests

KST = ZoneInfo("Asia/Seoul")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
# 여러 그룹에 보내려면 TELEGRAM_CHAT_ID 값에 쉼표로 구분해서 여러 chat_id를 넣는다.
# 예: -1003998809133,-1003775402640
CHAT_IDS = [c.strip() for c in os.environ["TELEGRAM_CHAT_ID"].split(",") if c.strip()]
SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
SHEET_GID = os.environ.get("GOOGLE_SHEET_GID", "0")
# 이 날짜를 1번째(순서상 첫 줄) 성구가 나가는 날로 고정한다.
START_DATE = date.fromisoformat(os.environ.get("START_DATE", "2026-09-15"))


def today_kst():
    # GitHub Actions 등 실행 서버는 UTC로 동작하므로, date.today()를 그대로 쓰면
    # 한국시간 00:00~08:59 구간에는 날짜가 하루 전으로 잘못 계산된다.
    return datetime.now(KST).date()

CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"


def fetch_verses():
    resp = requests.get(CSV_URL, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"  # 구글 시트 응답에 charset이 없어 requests가 잘못 추측하는 것을 방지
    reader = csv.DictReader(io.StringIO(resp.text))
    verses = []
    for row in reader:
        title = (row.get("성구 제목") or "").strip()
        content = (row.get("성구 내용") or "").strip()
        if title or content:
            verses.append({"title": title, "content": content})
    if not verses:
        raise ValueError("시트에서 성구를 하나도 읽어오지 못했습니다.")
    return verses


def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=20)
    resp.raise_for_status()
    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"텔레그램 전송 실패 (chat_id={chat_id}): {result}")


def main():
    verses = fetch_verses()
    today = today_kst()
    days_elapsed = (today - START_DATE).days
    idx = days_elapsed % len(verses)
    verse = verses[idx]

    today_str = today.strftime("%Y-%m-%d")
    message = f"[오늘의 성구] {today_str}\n\n{verse['title']}\n{verse['content']}"

    errors = []
    for chat_id in CHAT_IDS:
        try:
            send_telegram_message(chat_id, message)
            print(f"전송 완료 (chat_id={chat_id}, index={idx}): {verse['title']}")
        except Exception as e:
            errors.append(str(e))
            print(f"전송 실패 (chat_id={chat_id}): {e}")
    if errors:
        raise RuntimeError("; ".join(errors))


if __name__ == "__main__":
    main()
