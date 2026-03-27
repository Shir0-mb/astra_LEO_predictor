"""
main.py
LEO Pass Predictor for ASTRA — Loiano Observatory
Runs daily via GitHub Actions, sends report to Telegram.
"""

import sys
import os
import traceback
from datetime import datetime, timezone

from fetcher   import fetch_tles
from predictor import compute_passes
from formatter import format_report


def send_telegram(text: str):
    import requests
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id   = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    r = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }, timeout=30)
    if r.status_code == 200:
        print("[main] ✅ Report sent to Telegram!")
    else:
        print(f"[main] ❌ Telegram error: {r.status_code} {r.text}")
        raise RuntimeError("Failed to send Telegram message")


def send_error(msg: str):
    try:
        import requests
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id   = os.environ.get("TELEGRAM_CHAT_ID")
        if bot_token and chat_id:
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": f"⚠️ LEO Predictor error:\n{msg[:300]}"},
                timeout=15
            )
    except Exception:
        pass


def run():
    print("=" * 50)
    print("🛰  ASTRA LEO Pass Predictor starting...")
    print("=" * 50)

    # 1. Fetch TLEs
    print("\n[1/3] Fetching TLE catalog from Celestrak...")
    tles = fetch_tles(max_objects=3000)
    if not tles:
        raise RuntimeError("Failed to fetch TLEs from Celestrak")

    # 2. Compute passes
    print("\n[2/3] Computing visible passes over Loiano...")
    passes = compute_passes(tles, max_passes=25)

    # 3. Format and send
    print("\n[3/3] Sending report to Telegram...")
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    report   = format_report(passes, date_str)

    print("\n--- PREVIEW ---")
    print(report[:600])
    print("---------------\n")

    send_telegram(report)
    print("\n✅ Done!")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        tb = traceback.format_exc()
        print(f"\n❌ Error:\n{tb}", file=sys.stderr)
        send_error(str(e))
        sys.exit(1)
