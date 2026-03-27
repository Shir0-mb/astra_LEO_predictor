"""
fetcher.py
Downloads TLEs using Celestrak's newer GP query API (less restricted).
"""

import requests

HEADERS = {
    "User-Agent": "ASTRA-LEO-Predictor/1.0 (INAF-OAS Bologna; scientific use)"
}

def fetch_tles(max_objects: int = 3000) -> list[tuple[str, str, str]]:
    """Returns list of (name, line1, line2) tuples."""

    # Celestrak GP REST API — newer endpoint, less IP-blocked
    urls = [
        "https://celestrak.org/GP/query/?GROUP=active&FORMAT=tle",
        "https://celestrak.org/GP/query/?GROUP=starlink&FORMAT=tle",
        # Last resort: N2YO public mirror
        "https://www.n2yo.com/satellite/tle-list.php?group=active",
    ]

    for url in urls:
        try:
            print(f"[fetcher] Trying {url} ...")
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()

            text = r.text.strip()
            if not text or len(text) < 100:
                print(f"[fetcher] Empty response from {url}")
                continue

            lines = [l.strip() for l in text.splitlines() if l.strip()]
            tles = []
            for i in range(0, len(lines) - 2, 3):
                name  = lines[i]
                line1 = lines[i+1]
                line2 = lines[i+2]
                if line1.startswith("1 ") and line2.startswith("2 "):
                    tles.append((name, line1, line2))

            if tles:
                print(f"[fetcher] Got {len(tles)} TLEs from {url}")
                return tles[:max_objects]
            else:
                print(f"[fetcher] No valid TLEs parsed from {url}")

        except Exception as e:
            print(f"[fetcher] Failed {url}: {e}")
            continue

    return []
