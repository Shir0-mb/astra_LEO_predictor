"""
predictor.py
Computes LEO satellite passes over Loiano observatory for the next night.
Filters for: LEO only, visible passes (sat sunlit + observer dark), min elevation.
"""

from datetime import datetime, timedelta, timezone
from skyfield.api import load, wgs84, EarthSatellite
from skyfield.api import N, E
from skyfield import almanac
import numpy as np

# ── Observatory ───────────────────────────────────────────────────────────────
LOIANO_LAT  =  44.0 + 16/60   # 44°16'N
LOIANO_LON  =  11.0 + 19/60   # 11°19'E
LOIANO_ELEV =  0.841           # km (841 m)

MIN_ELEVATION_DEG = 20.0       # ignore passes below this elevation
MAX_LEO_PERIOD_MIN = 128.0     # orbital period threshold for LEO filter


def is_leo(line2: str) -> bool:
    """Check if object is LEO based on mean motion in TLE line 2."""
    try:
        mean_motion = float(line2[52:63])   # rev/day
        period_min  = 1440.0 / mean_motion
        return period_min < MAX_LEO_PERIOD_MIN
    except Exception:
        return False


def get_night_window(ts, observer_location):
    """Return (t_start, t_end) for the upcoming astronomical night from now."""
    now = datetime.now(timezone.utc)
    
    # Search window: next 24 hours
    t0 = ts.from_datetime(now)
    t1 = ts.from_datetime(now + timedelta(hours=24))

    # Find sunset/sunrise for tonight
    eph = load("de421.bsp")
    f   = almanac.dark_twilight_day(eph, observer_location)
    times, events = almanac.find_discrete(t0, t1, f)

    night_start = night_end = None
    for t, e in zip(times, events):
        if e == 0 and night_start is None:   # astronomical night begins
            night_start = t
        if e == 1 and night_start is not None:  # astronomical night ends
            night_end = t
            break

    # Fallback: use 20:00–06:00 local if almanac fails
    if night_start is None:
        night_start = ts.from_datetime(now.replace(hour=19, minute=0, second=0))
    if night_end is None:
        night_end = ts.from_datetime(
            (now + timedelta(days=1)).replace(hour=6, minute=0, second=0)
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

    night_start, night_end = get_night_window(ts, observer)

    print(f"[predictor] Night window: {night_start.utc_iso()} → {night_end.utc_iso()}")
    print(f"[predictor] Processing {len(tles)} TLEs (LEO filter + pass search)...")

    passes = []
    leo_count = 0

    for name, line1, line2 in tles:
        if not is_leo(line2):
            continue
        leo_count += 1

        try:
            sat = EarthSatellite(line1, line2, name, ts)

            # Find passes above MIN_ELEVATION_DEG
            t, events = sat.find_events(
                observer, night_start, night_end,
                altitude_degrees=MIN_ELEVATION_DEG
            )

            # Group into individual passes (rise=0, culminate=1, set=2)
            i = 0
            while i < len(events):
                if events[i] == 0:   # rise
                    rise_t = t[i]
                    culm_t = t[i+1] if i+1 < len(events) and events[i+1] == 1 else t[i]
                    set_t  = t[i+2] if i+2 < len(events) and events[i+2] == 2 else t[i]

                    # Check visibility: satellite sunlit during culmination?
                    diff    = sat - observer
                    topocentric = diff.at(culm_t)
                    alt, az, distance = topocentric.altaz()
                    sunlit  = sat.at(culm_t).is_sunlit(eph)

                    if sunlit and alt.degrees >= MIN_ELEVATION_DEG:
                        # Estimate magnitude (rough: based on distance and size ~1m²)
                        dist_km = distance.km
                        mag_est = -13.98 - 2.5 * np.log10(1.0 / dist_km**2) + 5.0  # rough

                        passes.append({
                            "name":     name.strip(),
                            "rise_utc": rise_t.utc_datetime().strftime("%H:%M"),
                            "culm_utc": culm_t.utc_datetime().strftime("%H:%M:%S"),
                            "set_utc":  set_t.utc_datetime().strftime("%H:%M"),
                            "max_el":   round(alt.degrees, 1),
                            "az_culm":  round(az.degrees, 1),
                            "dist_km":  round(dist_km),
                        })

                    i += 3
                else:
                    i += 1

        except Exception:
            continue

    passes.sort(key=lambda p: p["max_el"], reverse=True)
    print(f"[predictor] LEO objects: {leo_count} | Visible passes found: {len(passes)}")
    return passes[:max_passes]
