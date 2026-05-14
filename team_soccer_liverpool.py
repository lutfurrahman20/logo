"""
Liverpool FC - Player Headshot Scraper (Soccer / EPL)
Downloads headshots for a specific list of Liverpool players.

Sources (tried in order per player):
  0. LFC Official — backend.liverpoolfc.com current-season 2025-26 headshots
  1. ESPN CDN     — espncdn.com headshots via the ESPN soccer roster API (team 364)
  2. FPL CDN      — resources.premierleague.com/110x140 (current-season kit photos)
                    via Fantasy Premier League bootstrap API (team 12)

NOTE: FPL and ESPN CDN photos can be outdated for recently-transferred players.
      The LFC official website always serves current-season headshots.
NOTE: The legacy S3 CDN (platform-static-files.s3.amazonaws.com) is intentionally
NOT used — it serves outdated photos of players in their previous clubs' kits.

Squad verified against:
  https://www.espn.com/soccer/team/squad/_/id/364/liverpool
"""

import re
import time
import unicodedata
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ESPN_ROSTER_API = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/364/roster"
)
ESPN_HEADSHOT   = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

FPL_API       = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_CDN       = "https://resources.premierleague.com/premierleague/photos/players/110x140/p{code}.png"
LIV_FPL_ID    = 12   # Liverpool's team ID in the FPL API

LFC_FIRST_TEAM_URL = "https://www.liverpoolfc.com/team/first-team"

OUTPUT_DIR = Path("f:/logo/liverpool_soccer_player_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}
# ───────────────────────────────────────────────────────────────────────────────

# Exact player list to download
TARGET_PLAYERS = [
    "Alexander Isak",
    "Alexis Mac Allister",
    "Alisson Ramsés Becker",
    "Amara Nallo",
    "Andy Robertson",
    "Calvin Ramsay",
    "Carter Pinnington",
    "Cody Gakpo",
    "Conor Bradley",
    "Curtis Jones",
    "Dominik Szoboszlai",
    "Federico Chiesa",
    "Florian Wirtz",
    "Freddie Woodman",
    "Giorgi Mamardashvili",
    "Giovanni Leoni",
    "Hugo Ekitike",
    "Ibrahima Konaté",
    "Jayden Danns",
    "Jeremie Frimpong",
    "Joe Gomez",
    "Kaide Gordon",
    "Keyrol Figueroa",
    "Kieran Morrison",
    "Kornel Misciur",
    "Michael Laffey",
    "Milos Kerkez",
    "Mohamed Salah Hamed Mahrous Ghaly",
    "Rhys Williams",
    "Rio Ngumoha",
    "Ryan Gravenberch",
    "Stefan Bajcetic",
    "Tommy Pilling",
    "Trent Kone-Doherty",
    "Treymaurice Nyoni",
    "Virgil van Dijk",
    "Wataru Endo",
    "Wellity Lucky",
    "Ármin Pécsi",
]

# Maps full legal/user-supplied name → ESPN display name (for roster matching)
ESPN_NAME_OVERRIDES = {
    "Alisson Ramsés Becker":             "Alisson Becker",
    "Andy Robertson":                    "Andrew Robertson",
    "Mohamed Salah Hamed Mahrous Ghaly": "Mohamed Salah",
    "Ibrahima Konaté":                   "Ibrahima Konaté",
    "Stefan Bajcetic":                   "Stefan Bajcetic",
    "Treymaurice Nyoni":                 "Trey Nyoni",
    "Wataru Endo":                       "Endo Wataru",
    "Ármin Pécsi":                       "Ármin Pécsi",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Lower-case, strip accents, collapse whitespace."""
    nfkd   = unicodedata.normalize("NFKD", s)
    ascii_ = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_).strip().lower()


def safe_filename(name: str) -> str:
    """Return lower-case underscore filename (no accents, no special chars)."""
    name = name.strip()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name.lower()


def download_image(url: str, filepath: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 5000:
            filepath.write_bytes(r.content)
            return True
    except Exception as e:
        print(f"    ERROR    {e}")
    return False


def _squad_match(key: str, roster: dict) -> str | None:
    """
    Match normalized name against roster keys.
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
    return None


# ── Data sources ───────────────────────────────────────────────────────────────

def build_lfc_lookup() -> dict:
    """
    Scrapes https://www.liverpoolfc.com/team/first-team for 2025-26 headshots.
    Returns {normalized_player_name: image_url}.
    """
    lookup: dict = {}
    try:
        print("  Fetching LFC official first-team page ...")
        r = requests.get(LFC_FIRST_TEAM_URL, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"  WARNING  LFC page returned {r.status_code}")
            return {}
        raw_urls = re.findall(
            r'https://backend\.liverpoolfc\.com/sites/default/files/styles/[^/]+/public/[^"\'\'<>\s]+headshot[^"\'\'<>\s]*\.png',
            r.text
        )
        seen: dict = {}
        for url in raw_urls:
            xl_url = re.sub(r'/styles/[^/]+/', '/styles/xl/', url)
            filename = xl_url.split('/')[-1].rsplit('.', 1)[0]
            # strip hash: _{32hexchars}
            name_part = re.sub(r'_[0-9a-f]{32}$', '', filename, flags=re.I)
            # strip headshot suffix (with optional date prefix like -2526- or -2025-26-)
            name_part = re.sub(
                r'[-_](?:\d{4}(?:-\d{2})?[-_])?(?:profile[-_])?headshot.*$',
                '', name_part, flags=re.I
            )
            name_norm = name_part.replace('-', ' ').strip()
            if name_norm and name_norm not in seen:
                seen[name_norm] = xl_url
        lookup = seen
    except Exception as e:
        print(f"  WARNING  LFC fetch failed: {e}")
    return lookup


def build_espn_lookup() -> dict:
    """Returns {normalized_name: espn_player_id} for Liverpool's ESPN roster."""
    lookup: dict = {}
    try:
        print("  Fetching ESPN roster (team 364 / eng.1) ...")
        r = requests.get(ESPN_ROSTER_API, headers=HEADERS, timeout=20)
        r.raise_for_status()
        for athlete in r.json().get("athletes", []):
            pid  = str(athlete.get("id", ""))
            for n in (athlete.get("fullName", ""), athlete.get("displayName", "")):
                if n and pid:
                    lookup[normalize(n)] = pid
    except Exception as e:
        print(f"  WARNING  ESPN roster fetch failed: {e}")
    return lookup


def build_fpl_lookup() -> dict:
    """
    Returns {normalized_name: url} for every Liverpool player in FPL.
    Uses resources.premierleague.com/110x140 which has current-season photos.
    """
    lookup: dict = {}
    try:
        print("  Fetching Fantasy Premier League bootstrap ...")
        r = requests.get(FPL_API, headers=HEADERS, timeout=20)
        r.raise_for_status()
        for p in r.json().get("elements", []):
            if p.get("team") != LIV_FPL_ID:
                continue
            code  = p.get("code", "")
            first = p.get("first_name", "")
            last  = p.get("second_name", "")
            full  = f"{first} {last}".strip()
            if full and code:
                lookup[normalize(full)] = FPL_CDN.format(code=code)
    except Exception as e:
        print(f"  WARNING  FPL fetch failed: {e}")
    return lookup


def is_in_squad(player_name: str, espn_lookup: dict, fpl_lookup: dict, lfc_lookup: dict) -> bool:
    """Return True if the player appears in the Liverpool ESPN, FPL, or LFC official roster."""
    candidates = {normalize(player_name)}
    override = ESPN_NAME_OVERRIDES.get(player_name)
    if override:
        candidates.add(normalize(override))
    for key in candidates:
        if (_squad_match(key, espn_lookup) or _squad_match(key, fpl_lookup)
                or _squad_match(key, lfc_lookup)):
            return True
    return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("  Liverpool FC — Player Headshot Scraper")
    print("=" * 60)
    print(f"  Players to download : {len(TARGET_PLAYERS)}")
    print(f"  Output folder       : {OUTPUT_DIR}\n")

    lfc_lookup  = build_lfc_lookup()
    espn_lookup = build_espn_lookup()
    fpl_lookup  = build_fpl_lookup()
    print(f"\n  LFC official entries: {len(lfc_lookup)}")
    print(f"  ESPN roster entries : {len(espn_lookup)}")
    print(f"  FPL roster entries  : {len(fpl_lookup)}\n")
    print("-" * 60)
    print("Downloading headshots ...\n")

    results = {"downloaded": 0, "skipped": 0, "not_in_squad": 0, "no_image": 0}
    total   = len(TARGET_PLAYERS)

    for i, player_name in enumerate(TARGET_PLAYERS, 1):
        fname = safe_filename(player_name) + ".png"
        fpath = OUTPUT_DIR / fname

        print(f"  [{i:>2}/{total}] {player_name}")

        # ── Squad membership check ─────────────────────────────────────────────
        if not is_in_squad(player_name, espn_lookup, fpl_lookup, lfc_lookup):
            print(f"           Not in Liverpool squad — skipped")
            results["not_in_squad"] += 1
            continue

        if fpath.exists():
            print(f"           Already exists — skipped")
            results["skipped"] += 1
            continue

        img_url: str | None = None

        # ── 0. LFC Official (always current-season 2025-26 kit) ───────────────
        lfc_key     = normalize(player_name)
        matched_lfc = _squad_match(lfc_key, lfc_lookup)
        if not matched_lfc:
            override = ESPN_NAME_OVERRIDES.get(player_name)
            if override:
                matched_lfc = _squad_match(normalize(override), lfc_lookup)
        lfc_url = lfc_lookup.get(matched_lfc) if matched_lfc else None
        if lfc_url:
            try:
                r = requests.get(lfc_url, headers=HEADERS, timeout=15)
                if r.status_code == 200 and len(r.content) > 5000:
                    img_url = lfc_url
            except Exception:
                pass

        # ── 1. ESPN CDN ────────────────────────────────────────────────────────
        search_name  = ESPN_NAME_OVERRIDES.get(player_name, player_name)
        matched_espn = _squad_match(normalize(search_name), espn_lookup)
        if not matched_espn and search_name != player_name:
            matched_espn = _squad_match(normalize(player_name), espn_lookup)
        espn_id = espn_lookup.get(matched_espn) if matched_espn else None

        if espn_id:
            candidate = ESPN_HEADSHOT.format(id=espn_id)
            try:
                r = requests.get(candidate, headers=HEADERS, timeout=15)
                if r.status_code == 200 and len(r.content) > 5000:
                    img_url = candidate
            except Exception:
                pass

        # ── 2. FPL CDN (resources.premierleague.com 110x140, current-season) ──
        if not img_url:
            fpl_key     = normalize(player_name)
            matched_fpl = _squad_match(fpl_key, fpl_lookup)
            if not matched_fpl:
                override = ESPN_NAME_OVERRIDES.get(player_name)
                if override:
                    matched_fpl = _squad_match(normalize(override), fpl_lookup)
            fpl_url = fpl_lookup.get(matched_fpl) if matched_fpl else None

            if fpl_url:
                try:
                    r = requests.get(fpl_url, headers=HEADERS, timeout=15)
                    if r.status_code == 200 and len(r.content) > 5000:
                        img_url = fpl_url
                except Exception:
                    pass

        # ── Save or report ─────────────────────────────────────────────────────
        if img_url:
            ok = download_image(img_url, fpath)
            if ok:
                source = ("ESPN" if "espncdn" in img_url
                          else "LFC" if "liverpoolfc" in img_url
                          else "FPL")
                print(f"           [{source}] Saved → {fname}")
                results["downloaded"] += 1
            else:
                print(f"           Download failed")
                results["no_image"] += 1
        else:
            print(f"           No image found in any source")
            results["no_image"] += 1

        time.sleep(0.3)

    print("\n" + "=" * 60)
    print(f"  Done!")
    print(f"    Downloaded     : {results['downloaded']}")
    print(f"    Skipped        : {results['skipped']}  (already existed)")
    print(f"    Not in squad   : {results['not_in_squad']}  (not on Liverpool roster)")
    print(f"    No image found : {results['no_image']}")
    print(f"  Output folder: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
