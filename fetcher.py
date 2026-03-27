"""
fetcher.py
Downloads LEO TLE catalogs from Celestrak.
"""

import requests

HEADERS = {
    "User-Agent": "ASTRA-LEO-Predictor/1.0 (INAF-OAS Bologna; scientific use)"
}

CATALOG_URLS = [
    "https://celestrak.org/SOCRATES/query.php?CODE=ALL&MIN_RANGE=0&MAX_RANGE=2000&DAYS=7&MAX_MATCHES=1000&ORDERBY=DAYS&TLE=1&FORMAT=tle",
    "https://celestrak.org/pub/TLE/catalog.txt",
    "https://celestrak.org/SATCAT/tle.php",
]

# Smaller focused groups as fallback
GROUP_URLS = [
    "https://celestrak.org/SOCRATES/query.php?CODE=ALL",
    "https://celestrak.org/pub/TLE/active.txt",
    "https://celestrak.org/pub/TLE/stations.txt",
]

def fetch_tles(max_objects: int = 3000) -> list[tuple[str, str, str]]:
    """Returns list of (name, line1, line2) tuples."""
    
    urls = [
        "https://celestrak.org/pub/TLE/active.txt",   # ~6000 active satellites
        "https://celestrak.org/pub/TLE/catalog.txt",  # full catalog
    ]

    for url in urls:
        try:
            print(f"[fetcher] Trying {url} ...")
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            lines = [l.strip() for l in r.text.strip().splitlines() if l.strip()]
            tles = []
            for i in range(0, len(lines) - 2, 3):
                name  = lines[i]
                line1 = lines[i+1]
                line2 = lines[i+2]
                if line1.startswith("1 ") and line2.startswith("2 "):
                    tles.append((name, line1, line2))
            if tles:
                print(f"[fetcher] Got {len(tles)} TLEs")
                return tles[:max_objects]
        except Exception as e:
            print(f"[fetcher] Failed {url}: {e}")
            continue

    return []
