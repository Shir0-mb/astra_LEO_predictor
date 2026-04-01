"""
predictor.py
Computes LEO satellite passes over Loiano observatory for the next night.
Filters for: LEO only, visible passes (sat sunlit + observer dark), min elevation.
"""

from datetime import datetime, timedelta, timezone
from skyfield.api import load, wgs84, EarthSatellite, N, E
from skyfield import almanac
import numpy as np

# ── Observatory ───────────────────────────────────────────────────────────────
LOIANO_LAT  =  44.0 + 16/60   # 44°16'N
LOIANO_LON  =  11.0 + 19/60   # 11°19'E

MIN_ELEVATION_DEG  = 20.0
MAX_LEO_PERIOD_MIN = 128.0


def is_leo(line2: str) -> bool:
    try:
        mean_motion = float(line2[52:63])
        period_min  = 1440.0 / mean_motion
        return period_min < MAX_LEO_PERIOD_MIN
    except Exception:
        return False


def get_night_window(ts, eph, observer_location):
    """
    Return (t_start, t_end) for the upcoming astronomical night.
    Searches over the next 36 hours to correctly handle cross-midnight windows.
    """
    now = datetime.now(timezone.utc)
    t0  = ts.from_datetime(now)
    t1  = ts.from_datetime(now + timedelta(hours=36))

    f = almanac.dark_twilight_day(eph, observer_location)
    times, events = almanac.find_discrete(t0, t1, f)

    night_start = night_end = None
    for t, e in zip(times, events):
        # e=0: astronomical night starts (darkest)
        # e=1: nautical twilight starts (getting lighter)
        if e == 0 and night_start is None:
            night_start = t
        elif e >= 1 and night_start is not None and night_end is None:
            night_end = t
            break

    # Fallback: tonight 20:00 → tomorrow 05:00 UTC
    if night_start is None:
        start_dt = now.replace(hour=20, minute=0, second=0, microsecond=0)
        if now.hour > 20:
            start_dt += timedelta(days=1)
        night_start = ts.from_datetime(start_dt)

    if night_end is None:
        night_end = ts.from_datetime(
            night_start.utc_datetime() + timedelta(hours=9)
        )

    return night_start, night_end


def compute_passes(tles: list[tuple], max_passes: int = 30) -> list[dict]:
    """
    Compute visible LEO passes over Loiano for the next night.
    Returns list of pass dicts sorted by max elevation (descending).
    """
    ts       = load.timescale()
    eph      = load("de421.bsp")
    observer = wgs84.latlon(LOIANO_LAT * N, LOIANO_LON * E, elevation_m=841)

    night_start, night_end = get_night_window(ts, eph, observer)

    ns = night_start.utc_datetime()
    ne = night_end.utc_datetime()
    print(f"[predictor] Night window: {ns.strftime('%Y-%m-%d %H:%M')} → {ne.strftime('%Y-%m-%d %H:%M')} UTC")

    # Sanity check: end must be after start
    if night_end.tt <= night_start.tt:
        night_end = ts.from_datetime(ns + timedelta(hours=9))
        print(f"[predictor] Window was inverted, using fallback end: {night_end.utc_datetime()}")

    print(f"[predictor] Processing {len(tles)} TLEs (LEO filter + pass search)...")

    passes = []
    leo_count = 0

    for name, line1, line2 in tles:
        if not is_leo(line2):
            continue
        leo_count += 1

        try:
            sat = EarthSatellite(line1, line2, name, ts)
            t, events = sat.find_events(
                observer, night_start, night_end,
                altitude_degrees=MIN_ELEVATION_DEG
            )

            i = 0
            while i < len(events):
                if events[i] == 0:  # rise
                    rise_t = t[i]
                    culm_t = t[i+1] if (i+1 < len(events) and events[i+1] == 1) else t[i]
                    set_t  = t[i+2] if (i+2 < len(events) and events[i+2] == 2) else t[i]

                    diff       = sat - observer
                    topocentric = diff.at(culm_t)
                    alt, az, distance = topocentric.altaz()
                    sunlit     = sat.at(culm_t).is_sunlit(eph)

                    if sunlit and alt.degrees >= MIN_ELEVATION_DEG:
                        passes.append({
                            "name":     name.strip(),
                            "rise_utc": rise_t.utc_datetime().strftime("%H:%M"),
                            "culm_utc": culm_t.utc_datetime().strftime("%H:%M:%S"),
                            "set_utc":  set_t.utc_datetime().strftime("%H:%M"),
                            "max_el":   round(alt.degrees, 1),
                            "az_culm":  round(az.degrees, 1),
                            "dist_km":  round(distance.km),
                        })
                    i += 3
                else:
                    i += 1

        except Exception:
            continue

    passes.sort(key=lambda p: p["max_el"], reverse=True)
    print(f"[predictor] LEO objects: {leo_count} | Visible passes found: {len(passes)}")
    return passes[:max_passes]
