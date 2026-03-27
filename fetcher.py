"""
fetcher.py
Downloads LEO TLE catalogs from Celestrak (no auth required).
"""

import requests

# Celestrak supplemental catalogs covering most LEO objects
CELESTRAK_URLS = [
    "https://celestrak.org/SOCRATES/query.php?CODE=ALL&MIN_RANGE=0&MAX_RANGE=2000&DAYS=1&MAX_MATCHES=1000&ORDERBY=DAYS&TLE=1&FORMAT=tle",  # not ideal
]

# Better: use the main catalog groups
CATALOG_URLS = {
    "active":    "https://celestrak.org/SOCRATES/query.php",
    "stations":  "https://celestrak.org/SATCAT/tle.php?CATNR=25544",  # ISS only for test
}

# Curated Celestrak groups — covers active LEO population well
GROUPS = [
    "https://celestrak.org/SOCRATES/query.php?CODE=ALL",
]

def fetch_tles(max_objects: int = 2000) -> list[tuple[str, str, str]]:
    """
    Returns list of (name, line1, line2) tuples.
    Uses multiple Celestrak catalog groups to cover the LEO population.
    """
    catalog_urls = [
        "https://celestrak.org/pub/TLE/catalog.txt",              # full catalog ~10k objects
    ]

    # We use the full catalog and filter by period (LEO) in the predictor
    for url in catalog_urls:
        try:
            print(f"[fetcher] Downloading TLE catalog from Celestrak...")
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            lines = [l.strip() for l in r.text.strip().splitlines() if l.strip()]
            tles = []
            for i in range(0, len(lines) - 2, 3):
                name  = lines[i]
                line1 = lines[i+1]
                line2 = lines[i+2]
                if line1.startswith("1 ") and line2.startswith("2 "):
                    tles.append((name, line1, line2))
            print(f"[fetcher] Got {len(tles)} TLEs from catalog")
            return tles[:max_objects]
        except Exception as e:
            print(f"[fetcher] Failed {url}: {e}")

    return []
