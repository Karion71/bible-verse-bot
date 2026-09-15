"""
GitHub Actions 등 '매일 1회 실행 후 종료'되는 환경에서 쓰는 버전.
실행될 때마다 프로세스가 새로 뜨므로(상태 파일을 유지할 수 없으므로),
"기준일로부터 며칠째인지"를 계산해서 그 날짜에 해당하는 성구를 순서대로 보낸다.
목록 끝까지 가면 처음부터 순환한다.
"""

import csv
import io
import os
from datetime import date

import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
SHEET_GID = os.environ.get("GOOGLE_SHEET_GID", "0")
# 이 날짜를 1번째(순서상 첫 줄) 성구가 나가는 날로 고정한다.
START_DATE = date.fromisoformat(os.environ.get("START_DATE", "2026-09-15"))

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


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=20)
    resp.raise_for_status()
    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"텔레그램 전송 실패: {result}")


def main():
    verses = fetch_verses()
    days_elapsed = (date.today() - START_DATE).days
    idx = days_elapsed % len(verses)
    verse = verses[idx]

    today_str = date.today().strftime("%Y-%m-%d")
    message = f"[오늘의 성구] {today_str}\n\n{verse['title']}\n{verse['content']}"

    send_telegram_message(message)
    print(f"전송 완료 (index={idx}): {verse['title']}")


if __name__ == "__main__":
    main()
