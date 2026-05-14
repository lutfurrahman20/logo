"""
Clermont Foot 63 — Player Headshot Downloader (Soccer / Ligue 1)

Sources (tried in order per player):
  1. ESPN CDN      — a.espncdn.com headshots
  2. Transfermarkt — portrait photos (verein/3524)

Squad sourced from:
  https://www.espn.com/soccer/team/squad/_/id/3171/league/FRA.1
"""

import re
import time
import unicodedata
import requests
from pathlib import Path

ESPN_ROSTER_API = "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/teams/3171/roster"
ESPN_HEADSHOT   = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"
TM_KADER_URL    = "https://www.transfermarkt.com/clermont-foot-63/kader/verein/3524"
OUTPUT_DIR      = Path("f:/logo/clermont_foot_soccer_player_logos")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
TM_HEADERS = {**HEADERS, "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.transfermarkt.com/"}

_CHAR_MAP = str.maketrans({"ø":"o","Ø":"O","æ":"ae","Æ":"AE","ß":"ss","ł":"l","Ł":"L","ı":"i","ú":"u","á":"a","é":"e","è":"e","ê":"e","ë":"e","í":"i","ï":"i","î":"i","ó":"o","ô":"o","ü":"u","ù":"u","û":"u","ö":"o","ä":"a","â":"a","à":"a","ñ":"n","ç":"c","č":"c","š":"s","ž":"z","ř":"r","ě":"e","ý":"y"})

def normalize(s):
    s = s.translate(_CHAR_MAP)
    return re.sub(r"[-\s]+", " ", unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")).strip().lower()

def safe_filename(name):
    name = name.strip().translate(_CHAR_MAP)
    name = unicodedata.normalize("NFKD", name).encode("ascii","ignore").decode("ascii")
    return re.sub(r"[-\s]+","_", re.sub(r"[^\w\s-]","", name)).lower()

def download_image(url, filepath, hdrs=None, min_size=5000):
    try:
        r = requests.get(url, headers=hdrs or HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) >= min_size:
            filepath.write_bytes(r.content)
            return True
    except Exception as e:
        print(f"    ERROR {e}")
    return False

def _squad_match(key, roster):
    if key in roster: return key
    words, last = key.split(), key.split()[-1]
    for rk in roster:
        rw = rk.split()
        common = set(words) & set(rw)
        if len(common) >= 2: return rk
        if rw[-1] == last and len(common) >= 1: return rk
        if len(words) == 1 and words[0] in set(rw): return rk
    return None

def build_espn_roster():
    players = []
    try:
        r = requests.get(ESPN_ROSTER_API, headers=HEADERS, timeout=20)
        r.raise_for_status()
        for a in r.json().get("athletes", []):
            pid = str(a.get("id",""))
            name = a.get("displayName","") or a.get("fullName","")
            if pid and name:
                players.append({"display_name": name, "id": pid})
    except Exception as e:
        print(f"  WARNING ESPN failed: {e}")
    return players

def build_tm_lookup():
    lookup = {}
    try:
        r = requests.get(TM_KADER_URL, headers=TM_HEADERS, timeout=20)
        r.raise_for_status()
        for url, name in re.findall(r'data-src="(https://[^"]*portrait/medium/[^"]+)"[^>]*?alt="([^"]+)"', r.text):
            if name.strip():
                lookup[normalize(name.strip())] = url
        print(f"  Transfermarkt entries: {len(lookup)}")
    except Exception as e:
        print(f"  WARNING TM failed: {e}")
    return lookup

def tm_url_for(name, tm_lookup):
    matched = _squad_match(normalize(name), tm_lookup)
    if matched:
        try:
            r = requests.head(tm_lookup[matched], headers=TM_HEADERS, timeout=10)
            if r.status_code == 200: return tm_lookup[matched]
        except Exception: pass
    return None

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("  Clermont Foot 63 — Player Headshot Scraper")
    print("=" * 60)
    espn_roster = build_espn_roster()
    tm_lookup   = build_tm_lookup()
    print(f"\n  ESPN: {len(espn_roster)}  TM: {len(tm_lookup)}  Output: {OUTPUT_DIR}\n" + "-"*60)
    downloaded, skipped, no_image = 0, 0, []
    for i, player in enumerate(espn_roster, 1):
        name, eid = player["display_name"], player["id"]
        filename = safe_filename(name) + ".png"
        filepath = OUTPUT_DIR / filename
        print(f"  [{i:>2}/{len(espn_roster)}] {name}")
        if filepath.exists():
            print(f"           Already exists — skipped"); skipped += 1; continue
        url = ESPN_HEADSHOT.format(id=eid)
        if download_image(url, filepath):
            print(f"           [ESPN] Saved → {filename}"); downloaded += 1; time.sleep(0.3); continue
        url = tm_url_for(name, tm_lookup)
        if url and download_image(url, filepath, hdrs=TM_HEADERS, min_size=1000):
            print(f"           [TM  ] Saved → {filename}"); downloaded += 1; time.sleep(0.3); continue
        print(f"           No image found"); no_image.append(name)
    print(f"\n{'='*60}\n  Downloaded: {downloaded}  Skipped: {skipped}  No image: {len(no_image)}")
    for n in no_image: print(f"    - {n}")
    print(f"  Output: {OUTPUT_DIR}\n{'='*60}")

if __name__ == "__main__":
    main()
