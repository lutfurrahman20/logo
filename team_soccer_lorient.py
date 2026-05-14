"""
FC Lorient — Player Headshot Downloader (Soccer / Ligue 1)

Downloads headshots for all players in the ESPN squad roster.

Sources (tried in order per player):
  1. ESPN CDN      — a.espncdn.com headshots (primary for non-EPL teams)
  2. Transfermarkt — img.a.transfermarkt.technology portrait photos

Squad sourced from:
  https://www.espn.com/soccer/team/squad/_/id/273/lorient
"""

import re
import time
import unicodedata
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ESPN_ROSTER_API = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.2/teams/273/roster"
)
ESPN_HEADSHOT   = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

TM_KADER_URL    = "https://www.transfermarkt.com/fc-lorient/kader/verein/1158"

OUTPUT_DIR = Path("f:/logo/lorient_soccer_player_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

TM_HEADERS = {
    **HEADERS,
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.transfermarkt.com/",
}

# ── Character map for safe_filename / normalize ────────────────────────────────
_CHAR_MAP = str.maketrans({
    "ø": "o", "Ø": "O",
    "æ": "ae", "Æ": "AE",
    "ð": "d", "Ð": "D",
    "þ": "th", "Þ": "TH",
    "ß": "ss",
    "ł": "l", "Ł": "L",
    "ı": "i", "İ": "I",
    "ú": "u", "Ú": "U",
    "á": "a", "Á": "A",
    "é": "e", "É": "E",
    "è": "e", "È": "E",
    "ê": "e", "Ê": "E",
    "ë": "e", "Ë": "E",
    "í": "i", "Í": "I",
    "ï": "i", "Ï": "I",
    "î": "i", "Î": "I",
    "ó": "o", "Ó": "O",
    "ô": "o", "Ô": "O",
    "ü": "u", "Ü": "U",
    "ù": "u", "Ù": "U",
    "û": "u", "Û": "U",
    "ö": "o", "Ö": "O",
    "ä": "a", "Ä": "A",
    "â": "a", "Â": "A",
    "à": "a", "À": "A",
    "ñ": "n", "Ñ": "N",
    "ç": "c", "Ç": "C",
    "č": "c", "Č": "C",
    "š": "s", "Š": "S",
    "ž": "z", "Ž": "Z",
    "ř": "r", "Ř": "R",
    "ě": "e", "Ě": "E",
    "ý": "y", "Ý": "Y",
    "ï": "i",
})


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Lower-case, strip accents/special chars, collapse whitespace/hyphens."""
    s = s.translate(_CHAR_MAP)
    nfkd   = unicodedata.normalize("NFKD", s)
    ascii_ = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[-\s]+", " ", ascii_).strip().lower()


def safe_filename(name: str) -> str:
    """Return lower-case underscore filename (no accents, no special chars)."""
    name = name.strip().translate(_CHAR_MAP)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[-\s]+", "_", name)
    return name.lower()


def download_image(url: str, filepath: Path, hdrs: dict = None, min_size: int = 5000) -> bool:
    try:
        r = requests.get(url, headers=hdrs or HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) >= min_size:
            filepath.write_bytes(r.content)
            return True
    except Exception as e:
        print(f"    ERROR    {e}")
    return False


def _squad_match(key: str, roster: dict) -> str | None:
    """
    Fuzzy-match normalised name against roster keys.
    Accepts: exact match, OR 2+ shared words, OR same last word + 1 shared word.
    """
    if key in roster:
        return key
    words    = key.split()
    last     = words[-1]
    word_set = set(words)
    for rk in roster:
        rw     = rk.split()
        common = word_set & set(rw)
        if len(common) >= 2:
            return rk
        if rw[-1] == last and len(common) >= 1:
            return rk
        if len(words) == 1 and words[0] in set(rw):
            return rk
    return None


# ── Data-source builders ───────────────────────────────────────────────────────

def build_espn_roster() -> list[dict]:
    players = []
    # Try fra.1 (Ligue 1) first, fall back to fra.2 (Ligue 2)
    for league in ("fra.1", "fra.2"):
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/273/roster"

        try:
            print(f"  Fetching ESPN roster ({league}) ...")
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            data = r.json().get("athletes", [])
            if data:
                for athlete in data:
                    pid   = str(athlete.get("id", ""))
                    dname = athlete.get("displayName", "") or athlete.get("fullName", "")
                    if pid and dname:
                        players.append({"display_name": dname, "id": pid})
                print(f"  Found {len(players)} players via {league}")
                break
        except Exception as e:
            print(f"  WARNING  ESPN roster fetch failed ({league}): {e}")
    return players


def build_tm_lookup() -> dict:
    lookup: dict = {}
    try:
        print("  Fetching Transfermarkt squad page ...")
        r = requests.get(TM_KADER_URL, headers=TM_HEADERS, timeout=20)
        r.raise_for_status()
        pairs = re.findall(
            r'data-src="(https://[^"]*portrait/medium/[^"]+)"[^>]*?alt="([^"]+)"',
            r.text,
        )
        for url, name in pairs:
            name = name.strip()
            if name:
                lookup[normalize(name)] = url
        print(f"  Transfermarkt entries: {len(lookup)}")
    except Exception as e:
        print(f"  WARNING  Transfermarkt fetch failed: {e}")
    return lookup


def tm_url_for(espn_display_name: str, tm_lookup: dict) -> str | None:
    key     = normalize(espn_display_name)
    matched = _squad_match(key, tm_lookup)
    if matched:
        url = tm_lookup[matched]
        try:
            r = requests.head(url, headers=TM_HEADERS, timeout=10)
            if r.status_code == 200:
                return url
        except Exception:
            pass
    return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  FC Lorient — Player Headshot Scraper")
    print("=" * 60)

    espn_roster = build_espn_roster()
    tm_lookup   = build_tm_lookup()

    print(f"\n  ESPN roster entries : {len(espn_roster)}")
    print(f"  TM  roster entries  : {len(tm_lookup)}")
    print(f"\n  Output: {OUTPUT_DIR}\n")
    print("-" * 60)

    downloaded = 0
    skipped    = 0
    no_image   = []

    for i, player in enumerate(espn_roster, 1):
        name     = player["display_name"]
        espn_id  = player["id"]
        filename = safe_filename(name) + ".png"
        filepath = OUTPUT_DIR / filename

        print(f"  [{i:>2}/{len(espn_roster)}] {name}")

        if filepath.exists():
            print(f"           Already exists — skipped")
            skipped += 1
            continue

        # ── 1. ESPN CDN ───────────────────────────────────────────────────────
        url = ESPN_HEADSHOT.format(id=espn_id)
        if download_image(url, filepath):
            print(f"           [ESPN] Saved → {filename}")
            downloaded += 1
            time.sleep(0.3)
            continue

        # ── 2. Transfermarkt portrait ─────────────────────────────────────────
        url = tm_url_for(name, tm_lookup)
        if url and download_image(url, filepath, hdrs=TM_HEADERS, min_size=1000):
            print(f"           [TM  ] Saved → {filename}")
            downloaded += 1
            time.sleep(0.3)
            continue

        print(f"           No image found in any source")
        no_image.append(name)

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Downloaded  : {downloaded}")
    print(f"  Skipped     : {skipped}")
    print(f"  No image    : {len(no_image)}")
    if no_image:
        for n in no_image:
            print(f"    - {n}")
    print(f"  Output      : {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
