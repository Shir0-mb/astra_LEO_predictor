"""
formatter.py
Formats the pass list into a readable Telegram message.
No LLM needed here — this is structured data, plain formatting is better and cheaper.
"""

from datetime import datetime, timezone


def az_to_direction(az: float) -> str:
    dirs = ["N","NE","E","SE","S","SW","W","NW","N"]
    return dirs[round(az / 45) % 8]


def format_report(passes: list[dict], date_str: str = None) -> str:
    if not date_str:
        date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    if not passes:
        return (
            f"🔭 ASTRA — LEO Pass Forecast\n"
            f"Loiano | {date_str}\n"
            f"─────────────────────────────\n"
            f"No visible passes tonight.\n"
            f"(Cloudy forecast or no sunlit LEO objects above {20}°)"
        )

    lines = [
        f"🛰 ASTRA — LEO Pass Forecast",
        f"Loiano | Tonight | {date_str}",
        f"Min elevation: 20° | Times: UTC",
        f"─────────────────────────────",
    ]

    for i, p in enumerate(passes, 1):
        direction = az_to_direction(p["az_culm"])
        lines.append(
            f"\n#{i} {p['name']}\n"
            f"   Rise {p['rise_utc']} → Max {p['max_el']}° ({direction}) → Set {p['set_utc']}\n"
            f"   Culmination: {p['culm_utc']} | Dist: {p['dist_km']} km"
        )

    lines.append(f"\n─────────────────────────────")
    lines.append(f"Total visible passes: {len(passes)}")
    lines.append(f"Sorted by max elevation")

    full = "\n".join(lines)

    # Telegram 4096 char limit
    if len(full) > 4000:
        full = full[:3990] + "\n..."

    return full
