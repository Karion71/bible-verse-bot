"""
매일 정해진 시간에 구글 시트의 성구를 순서대로 텔레그램 그룹에 전송하는 봇.
- 구글 시트를 CSV로 읽어온다 (공유 링크: 링크가 있는 모든 사용자 - 뷰어).
- state.json 에 "다음에 보낼 순서(인덱스)"를 저장해서, 재시작해도 이어서 보낸다.
- 목록 끝까지 가면 처음부터 다시 순환한다.
"""

import csv
import io
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
SHEET_GID = os.environ.get("GOOGLE_SHEET_GID", "0")
SEND_HOUR = int(os.environ.get("SEND_HOUR", "6"))
SEND_MINUTE = int(os.environ.get("SEND_MINUTE", "0"))

STATE_FILE = BASE_DIR / "state.json"
LOG_FILE = BASE_DIR / "bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

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
        raise ValueError("시트에서 성구를 하나도 읽어오지 못했습니다. 열 이름을 확인하세요.")
    return verses


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"next_index": 0}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=20)
    resp.raise_for_status()
    result = resp.json()
    if not result.get("ok"):
        raise RuntimeError(f"텔레그램 전송 실패: {result}")


def send_daily_verse():
    try:
        verses = fetch_verses()
        state = load_state()
        idx = state.get("next_index", 0) % len(verses)
        verse = verses[idx]

        today = datetime.now().strftime("%Y-%m-%d")
        message = f"[오늘의 성구] {today}\n\n{verse['title']}\n{verse['content']}"

        send_telegram_message(message)
        log.info("전송 완료 (index=%d): %s", idx, verse["title"])

        state["next_index"] = (idx + 1) % len(verses)
        save_state(state)
    except Exception:
        log.exception("성구 전송 중 오류 발생")


def main():
    log.info(
        "봇 시작. 매일 %02d:%02d(KST)에 전송합니다. (Ctrl+C로 종료)",
        SEND_HOUR,
        SEND_MINUTE,
    )
    scheduler = BlockingScheduler(timezone="Asia/Seoul")
    scheduler.add_job(
        send_daily_verse,
        trigger=CronTrigger(hour=SEND_HOUR, minute=SEND_MINUTE, timezone="Asia/Seoul"),
        id="daily_verse",
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("봇 종료")


if __name__ == "__main__":
    main()
