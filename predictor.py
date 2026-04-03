"""
predictor.py
Computes LEO satellite passes over Loiano observatory for the next night.

Observing windows based on Buzzoni (2016):
"For mid-latitude ground sensors, a maximum observing proficiency is achieved
within the first 100±12 min following/preceding the nautical twilight."
→ Two windows per night:
    EW (Evening Window): nautical_sunset  → nautical_sunset  + 110 min
    MW (Morning Window): nautical_sunrise - 110 min → nautical_sunrise

Orbit classification (added 2026-04-03):
    STABLE → 200 km ≤ perigee AND apogee ≤ 1500 km
    DECAY  → perigee < 200 km
"""

from datetime import datetime, timedelta, timezone
from skyfield.api import load, wgs84, EarthSatellite, N, E
from skyfield import almanac
import numpy as np

# ── Observatory ───────────────────────────────────────────────────────────────
LOIANO_LAT  = 44.0 + 16/60   # 44°16'N
LOIANO_LON  = 11.0 + 19/60   # 11°19'E

MIN_ELEVATION_DEG  = 20.0
MAX_LEO_PERIOD_MIN = 128.0
BUZZONI_WINDOW_MIN = 110      # minutes after/before nautical twilight

# ── Orbital classification ────────────────────────────────────────────────────
EARTH_RADIUS_KM = 6371.0
GM_KM3_S2       = 398600.4418   # Earth gravitational parameter


def classify_orbit(line2: str) -> dict:
    """
    Compute perigee, apogee and orbit class from TLE line 2.

    Returns:
        {
            "perigee_km":   float,
            "apogee_km":    float,
            "orbit_class":  "STABLE" | "DECAY",
        }
    """
    try:
        mean_motion_rev_day = float(line2[52:63])
        eccentricity        = float("0." + line2[26:33].strip())

        n_rad_s  = mean_motion_rev_day * 2 * np.pi / 86400.0
        a_km     = (GM_KM3_S2 / n_rad_s**2) ** (1/3)

        perigee_km = a_km * (1 - eccentricity) - EARTH_RADIUS_KM
        apogee_km  = a_km * (1 + eccentricity) - EARTH_RADIUS_KM

        if perigee_km < 200.0:
            orbit_class = "DECAY"
        else:
            orbit_class = "STABLE"

        return {
            "perigee_km":  round(perigee_km),
            "apogee_km":   round(apogee_km),
            "orbit_class": orbit_class,
        }

    except Exception:
        return {
            "perigee_km":  None,
            "apogee_km":   None,
            "orbit_class": "UNKNOWN",
        }


def is_leo(line2: str) -> bool:
    try:
        mean_motion = float(line2[52:63])
        return (1440.0 / mean_motion) < MAX_LEO_PERIOD_MIN
    except Exception:
        return False


def get_observation_windows(ts, eph, observer):
    """
    Returns two Skyfield time pairs:
        (ew_start, ew_end)  — Evening Window
        (mw_start, mw_end)  — Morning Window

    Based on Buzzoni (2016): optimal LEO visibility within 110 min
    of nautical twilight at sunset and sunrise.
    """
    now = datetime.now(timezone.utc)
    t0  = ts.from_datetime(now)
    t1  = ts.from_datetime(now + timedelta(hours=36))

    # dark_twilight_day events:
    #   0 = astronomical night
    #   1 = astronomical twilight
    #   2 = nautical twilight      ← we want this
    #   3 = civil twilight
    #   4 = day
    f = almanac.dark_twilight_day(eph, observer)
    times, events = almanac.find_discrete(t0, t1, f)

    nautical_sunset  = None   # transition 3→2 or 4→2 (getting darker, crosses nautical)
    nautical_sunrise = None   # transition 2→3 or 2→4 (getting lighter, crosses nautical)

    for i in range(len(events) - 1):
        e_before = events[i]
        e_after  = events[i+1]
        t_cross  = times[i+1]

        # Evening: brightness decreasing, crossing nautical threshold (3→2)
        if e_before >= 3 and e_after <= 2 and nautical_sunset is None:
            nautical_sunset = t_cross

        # Morning: brightness increasing, crossing nautical threshold (2→3)
        if e_before <= 2 and e_after >= 3 and nautical_sunset is not None and nautical_sunrise is None:
            nautical_sunrise = t_cross
            break

    # Build windows
    delta = timedelta(minutes=BUZZONI_WINDOW_MIN)

    if nautical_sunset is not None:
        ew_start = nautical_sunset
        ew_end   = ts.from_datetime(nautical_sunset.utc_datetime() + delta)
    else:
        # Fallback: 19:30 UTC + 110 min
        fb = now.replace(hour=19, minute=30, second=0, microsecond=0)
        ew_start = ts.from_datetime(fb)
        ew_end   = ts.from_datetime(fb + delta)

    if nautical_sunrise is not None:
        mw_end   = nautical_sunrise
        mw_start = ts.from_datetime(nautical_sunrise.utc_datetime() - delta)
    else:
        # Fallback: 04:00 UTC - 110 min
        fb = (now + timedelta(days=1)).replace(hour=4, minute=0, second=0, microsecond=0)
        mw_end   = ts.from_datetime(fb)
        mw_start = ts.from_datetime(fb - delta)

    return (ew_start, ew_end), (mw_start, mw_end)


def find_passes_in_window(sat, observer, eph, t_start, t_end, ts,
                          orbit_info: dict) -> list[dict]:
    """Find all visible passes for a single satellite in a given time window."""
    passes = []
    try:
        t, events = sat.find_events(
            observer, t_start, t_end,
            altitude_degrees=MIN_ELEVATION_DEG
        )
        i = 0
        while i < len(events):
            if events[i] == 0:  # rise
                rise_t = t[i]
                culm_t = t[i+1] if (i+1 < len(events) and events[i+1] == 1) else t[i]
                set_t  = t[i+2] if (i+2 < len(events) and events[i+2] == 2) else t[i]

                topo = (sat - observer).at(culm_t)
                alt, az, distance = topo.altaz()
                sunlit = sat.at(culm_t).is_sunlit(eph)

                if sunlit and alt.degrees >= MIN_ELEVATION_DEG:
                    passes.append({
                        "name":        sat.name.strip(),
                        "rise_utc":    rise_t.utc_datetime().strftime("%H:%M"),
                        "culm_utc":    culm_t.utc_datetime().strftime("%H:%M:%S"),
                        "set_utc":     set_t.utc_datetime().strftime("%H:%M"),
                        "max_el":      round(alt.degrees, 1),
                        "az_culm":     round(az.degrees, 1),
                        "dist_km":     round(distance.km),
                        "perigee_km":  orbit_info["perigee_km"],
                        "apogee_km":   orbit_info["apogee_km"],
                        "orbit_class": orbit_info["orbit_class"],
                    })
                i += 3
            else:
                i += 1
    except Exception:
        pass
    return passes


def compute_passes(tles: list[tuple], max_passes: int = 25) -> dict:
    """
    Compute visible LEO passes over Loiano using Buzzoni (2016) windows.
    Returns dict with keys 'evening' and 'morning', each a list of pass dicts.
    """
    ts       = load.timescale()
    eph      = load("de421.bsp")
    observer = wgs84.latlon(LOIANO_LAT * N, LOIANO_LON * E, elevation_m=841)

    (ew_start, ew_end), (mw_start, mw_end) = get_observation_windows(ts, eph, observer)

    print(f"[predictor] Evening Window: "
          f"{ew_start.utc_datetime().strftime('%H:%M')} → "
          f"{ew_end.utc_datetime().strftime('%H:%M')} UTC "
          f"({BUZZONI_WINDOW_MIN} min after nautical sunset)")
    print(f"[predictor] Morning Window: "
          f"{mw_start.utc_datetime().strftime('%H:%M')} → "
          f"{mw_end.utc_datetime().strftime('%H:%M')} UTC "
          f"({BUZZONI_WINDOW_MIN} min before nautical sunrise)")
    print(f"[predictor] Processing {len(tles)} TLEs...")

    evening_passes = []
    morning_passes = []
    leo_count = 0

    for name, line1, line2 in tles:
        if not is_leo(line2):
            continue
        leo_count += 1

        orbit_info = classify_orbit(line2)
        sat        = EarthSatellite(line1, line2, name, ts)

        evening_passes.extend(
            find_passes_in_window(sat, observer, eph, ew_start, ew_end, ts, orbit_info)
        )
        morning_passes.extend(
            find_passes_in_window(sat, observer, eph, mw_start, mw_end, ts, orbit_info)
        )

    evening_passes.sort(key=lambda p: p["max_el"], reverse=True)
    morning_passes.sort(key=lambda p: p["max_el"], reverse=True)

    print(f"[predictor] LEO objects: {leo_count} | "
          f"Evening: {len(evening_passes)} passes | "
          f"Morning: {len(morning_passes)} passes")

    return {
        "evening":  evening_passes[:max_passes],
        "morning":  morning_passes[:max_passes],
        "ew_start": ew_start.utc_datetime().strftime("%H:%M"),
        "ew_end":   ew_end.utc_datetime().strftime("%H:%M"),
        "mw_start": mw_start.utc_datetime().strftime("%H:%M"),
        "mw_end":   mw_end.utc_datetime().strftime("%H:%M"),
    }
