"""
fetcher.py
Downloads TLEs from Space-Track.org (official USSPACECOM source).
Requires free registration at https://www.space-track.org/auth/createAccount
"""

import requests

BASE_URL = "https://www.space-track.org"
LOGIN_URL = f"{BASE_URL}/ajaxauth/login"
# Query: active LEO objects only
# DECAY_DATE/null-val  → excludes re-entered objects
# MEAN_MOTION/>11.25   → LEO filter (period < 128 min)
# EPOCH/>now-3         → TLE no older than 3 days
QUERY_URL = (
    f"{BASE_URL}/basicspacedata/query/class/gp"
    f"/DECAY_DATE/null-val"
    f"/MEAN_MOTION/%3E11.25"
    f"/EPOCH/%3Enow-3"
    f"/orderby/NORAD_CAT_ID"
    f"/format/tle"
    f"/limit/5000"
)

def fetch_tles(max_objects: int = 3000) -> list[tuple[str, str, str]]:
    """
    Logs into Space-Track.org and downloads LEO TLEs.
    Requires SPACETRACK_USER and SPACETRACK_PASS environment variables.
    """
    import os
    username = os.environ.get("SPACETRACK_USER")
    password = os.environ.get("SPACETRACK_PASS")

    if not username or not password:
        raise RuntimeError(
            "SPACETRACK_USER and SPACETRACK_PASS environment variables not set. "
            "Register for free at https://www.space-track.org/auth/createAccount"
        )

    session = requests.Session()
    session.headers.update({
        "User-Agent": "ASTRA-LEO-Predictor/1.0 (INAF-OAS Bologna; scientific use)"
    })

    # Login
    print("[fetcher] Logging into Space-Track.org...")
    resp = session.post(LOGIN_URL, data={
        "identity": username,
        "password": password
    }, timeout=30)
    resp.raise_for_status()
    if "Login" in resp.text and "Failed" in resp.text:
        raise RuntimeError("Space-Track login failed — check credentials")

    # Download LEO TLEs
    print("[fetcher] Downloading LEO TLEs (MEAN_MOTION > 11.25 rev/day)...")
    resp = session.get(QUERY_URL, timeout=60)
    resp.raise_for_status()

    lines = [l.strip() for l in resp.text.strip().splitlines() if l.strip()]
    tles = []

    # Detect 2-line vs 3-line format
    # Space-Track often returns 2-line TLEs (no name line)
    if lines and lines[0].startswith("1 "):
        # 2-line format: extract NORAD ID as name
        for i in range(0, len(lines) - 1, 2):
            line1 = lines[i]
            line2 = lines[i+1] if i+1 < len(lines) else ""
            if line1.startswith("1 ") and line2.startswith("2 "):
                norad = line1[2:7].strip()
                tles.append((f"NORAD-{norad}", line1, line2))
    else:
        # 3-line format: name + line1 + line2
        for i in range(0, len(lines) - 2, 3):
            name  = lines[i]
            line1 = lines[i+1]
            line2 = lines[i+2]
            if line1.startswith("1 ") and line2.startswith("2 "):
                tles.append((name, line1, line2))

    print(f"[fetcher] Got {len(tles)} LEO TLEs from Space-Track")
    return tles[:max_objects]
