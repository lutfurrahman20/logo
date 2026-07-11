"""
Tottenham Hotspur FC — Player Headshot Downloader (Soccer / EPL)

Downloads headshots for all players in the ESPN squad roster.

Sources (tried in order per player):
  1. PL25 CDN      — resources.premierleague.com/premierleague25/110x140 (2025/26 kits)
                     No 'p' prefix. Covers 38 of 45 FPL squad members.
  2. FPL CDN       — resources.premierleague.com/premierleague/110x140 (legacy fallback).
  3. Transfermarkt — img.a.transfermarkt.technology portrait photos (28 players).
  4. ESPN CDN      — espncdn.com headshots (last resort).

NOTE: The legacy S3 CDN (platform-static-files.s3.amazonaws.com) is intentionally
      NOT used — it serves outdated photos of players in previous clubs' kits.

Squad sourced from:
  https://www.espn.com/soccer/team/squad/_/id/367/tottenham-hotspur
"""

import re
import time
import unicodedata
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ESPN_ROSTER_API   = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/367/roster"
)
ESPN_HEADSHOT     = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

FPL_API           = "https://fantasy.premierleague.com/api/bootstrap-static/"
PL25_CDN          = "https://resources.premierleague.com/premierleague25/photos/players/110x140/{code}.png"
FPL_CDN           = "https://resources.premierleague.com/premierleague/photos/players/110x140/p{code}.png"
SPURS_FPL_ID      = 18

TM_KADER_URL      = "https://www.transfermarkt.com/tottenham-hotspur/kader/verein/148"

OUTPUT_DIR = Path("f:/logo/tottenham_hotspur_soccer_player_logos")

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

# ── ESPN display-name → FPL full name overrides ────────────────────────────────
ESPN_TO_FPL_NAME: dict[str, str] = {
    # Add overrides here if ESPN name differs significantly from FPL name
    # "Souza" is single-name on ESPN/TM — _squad_match handles it automatically
}

# ── Character map for safe_filename / normalize ────────────────────────────────
_CHAR_MAP = str.maketrans({
    "ø": "o", "Ø": "O",
    "æ": "ae", "Æ": "AE",
    "ð": "d", "Ð": "D",
    "þ": "th", "Þ": "TH",
    "ß": "ss",
    "ł": "l", "Ł": "L",
    "ı": "i", "İ": "I",   # Turkish dotless-i
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
    Single-word keys match any roster entry containing that word.
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
    try:
        print("  Fetching ESPN roster (team 367 / eng.1) ...")
        r = requests.get(ESPN_ROSTER_API, headers=HEADERS, timeout=20)
        r.raise_for_status()
        for athlete in r.json().get("athletes", []):
            pid   = str(athlete.get("id", ""))
            dname = athlete.get("displayName", "") or athlete.get("fullName", "")
            if pid and dname:
                players.append({"display_name": dname, "id": pid})
    except Exception as e:
        print(f"  WARNING  ESPN roster fetch failed: {e}")
    return players


def build_fpl_lookup() -> dict:
    """
    Returns {normalized_name: best_photo_url} for every Spurs player in FPL.
    Primary key → PL25 CDN (2025/26 current-kit).
    __fallback key → legacy FPL CDN.
    """
    lookup: dict = {}
    try:
        print("  Fetching Fantasy Premier League bootstrap ...")
        r = requests.get(FPL_API, headers=HEADERS, timeout=30)
        r.raise_for_status()
        for p in r.json().get("elements", []):
            if p.get("team") != SPURS_FPL_ID:
                continue
            code  = p.get("code", "")
            first = p.get("first_name", "")
            last  = p.get("second_name", "")
            full  = f"{first} {last}".strip()
            if not (full and code):
                continue
            key = normalize(full)
            lookup[key]                = PL25_CDN.format(code=code)
            lookup[key + "__fallback"] = FPL_CDN.format(code=code)
    except Exception as e:
        print(f"  WARNING  FPL fetch failed: {e}")
    return lookup


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


# ── URL resolvers ──────────────────────────────────────────────────────────────

def fpl_url_for(espn_display_name: str, fpl_lookup: dict) -> str | None:
    """Try PL25 CDN first, then legacy FPL CDN. Returns first that responds 200."""
    candidates = [espn_display_name]
    override = ESPN_TO_FPL_NAME.get(espn_display_name)
    if override:
        candidates.append(override)

    for name in candidates:
        key     = normalize(name)
        matched = _squad_match(key, fpl_lookup)
        if matched:
            for url_key in [matched, matched + "__fallback"]:
                url = fpl_lookup.get(url_key)
                if not url:
                    continue
                try:
                    r = requests.head(url, headers=HEADERS, timeout=10)
                    if r.status_code == 200:
                        return url
                except Exception:
                    pass
    return None


def tm_url_for(espn_display_name: str, tm_lookup: dict) -> str | None:
    candidates = [espn_display_name]
    override = ESPN_TO_FPL_NAME.get(espn_display_name)
    if override:
        candidates.append(override)

    for name in candidates:
        key     = normalize(name)
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
    print("  Tottenham Hotspur FC — Player Headshot Scraper")
    print("=" * 60)

    espn_roster = build_espn_roster()
    fpl_lookup  = build_fpl_lookup()
    tm_lookup   = build_tm_lookup()

    print(f"\n  ESPN roster entries : {len(espn_roster)}")
    print(f"  FPL roster entries  : {len([k for k in fpl_lookup if not k.endswith('__fallback')])}")
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

        # ── 1. PL25 / FPL CDN ─────────────────────────────────────────────────
        url = fpl_url_for(name, fpl_lookup)
        if url and download_image(url, filepath):
            tag = "PL25" if "premierleague25" in url else "FPL "
            print(f"           [{tag}] Saved → {filename}")
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

        # ── 3. ESPN CDN ───────────────────────────────────────────────────────
        url = ESPN_HEADSHOT.format(id=espn_id)
        if download_image(url, filepath):
            print(f"           [ESPN] Saved → {filename}")
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
