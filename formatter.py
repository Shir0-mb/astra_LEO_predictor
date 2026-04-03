"""
formatter.py
Formats the pass dict (evening + morning windows) into a Telegram message.
Based on Buzzoni (2016) two-window observing strategy.
"""

from datetime import datetime, timezone


def az_to_direction(az: float) -> str:
    dirs = ["N","NE","E","SE","S","SW","W","NW","N"]
    return dirs[round(az / 45) % 8]


def format_pass_list(passes: list[dict]) -> str:
    if not passes:
        return "   No visible passes in this window.\n"
    lines = []
    for i, p in enumerate(passes, 1):
        direction = az_to_direction(p["az_culm"])
        lines.append(
            f"  #{i} {p['name']}\n"
            f"     Rise {p['rise_utc']} → Max {p['max_el']}° ({direction}) → Set {p['set_utc']}\n"
            f"     Culmination: {p['culm_utc']} UTC | Dist: {p['dist_km']} km"
        )
    return "\n".join(lines) + "\n"


def format_report(result: dict, date_str: str = None) -> str:
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    evening = result.get("evening", [])
    morning = result.get("morning", [])
    ew_start = result.get("ew_start", "?")
    ew_end   = result.get("ew_end",   "?")
    mw_start = result.get("mw_start", "?")
    mw_end   = result.get("mw_end",   "?")
    total    = len(evening) + len(morning)

    lines = [
        f"🛰 ASTRA — LEO Pass Forecast",
        f"Loiano | {date_str} | Times: UTC",
        f"Ref: Buzzoni (2016) — 110 min windows",
        f"─────────────────────────────",
        f"",
        f"🌆 EVENING WINDOW  {ew_start}–{ew_end} UTC",
        f"   (110 min after nautical sunset)",
        f"",
        format_pass_list(evening),
        f"🌅 MORNING WINDOW  {mw_start}–{mw_end} UTC",
        f"   (110 min before nautical sunrise)",
        f"",
        format_pass_list(morning),
        f"─────────────────────────────",
        f"Total visible passes: {total} | Min elevation: 20°",
    ]

    full = "\n".join(lines)
    if len(full) > 4000:
        full = full[:3990] + "\n..."
    return full
