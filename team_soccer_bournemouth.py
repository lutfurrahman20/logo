"""
AFC Bournemouth — Player Headshot Downloader (Soccer / EPL)

Downloads headshots for all players in the ESPN squad roster.

Sources (tried in order per player):
  1. FPL CDN      — resources.premierleague.com/110x140 (current-season kit photos)
                    via Fantasy Premier League bootstrap API (team 4).
                    Covers ~25 established squad members.
  2. Transfermarkt — img.a.transfermarkt.technology portrait photos.
                    Fallback for players not yet in the FPL CDN  (new arrivals,
                    youth players).  NOTE: TM portraits may not be in Bournemouth
                    kit for very recent signings.
  3. ESPN CDN      — espncdn.com headshots via ESPN roster API (team 349).
                    Very sparse — used only as last resort.

NOTE: The legacy S3 CDN (platform-static-files.s3.amazonaws.com) is intentionally
      NOT used — it serves outdated photos of players in previous clubs' kits.
NOTE: The AFCB official website (afcb.co.uk) uses a fully client-side SPA;
      its media CDN and CMS APIs are auth-gated (401 Unauthorized).

Squad sourced from:
  https://www.espn.com/soccer/team/squad/_/id/349/afc-bournemouth
"""

import re
import time
import unicodedata
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ESPN_ROSTER_API  = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/349/roster"
)
ESPN_HEADSHOT    = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

FPL_API          = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_CDN          = "https://resources.premierleague.com/premierleague/photos/players/110x140/p{code}.png"
BOURNEMOUTH_FPL_ID = 4

TM_KADER_URL     = "https://www.transfermarkt.com/afc-bournemouth/kader/verein/989"
TM_PORTRAIT_CDN  = "https://img.a.transfermarkt.technology/portrait/medium/"

OUTPUT_DIR = Path("f:/logo/bournemouth_soccer_player_logos")

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
# Where ESPN uses a shortened or hyphenated form that differs from FPL's full name.
ESPN_TO_FPL_NAME = {
    "Ben Gannon Doak":    "Ben Gannon-Doak",          # hyphen difference
    "Evanilson":          "Francisco Evanilson de Lima Barbosa",
    "Rayan":              "Rayan Vitor Simplício Rocha",
    "Marcos Senesi":      "Marcos Senesi Barón",
    "Djordje Petrovic":   "Đorđe Petrović",
    "Enes Ünal":          "Enes Ünal",
    "Álex Jiménez":       "Álex Jiménez Sánchez",
    "Bafodé Diakité":     "Bafodé Diakité",
    "Julio Soler":        "Julio Soler Barreto",
    "Junior Kroupi":      "Junior Kroupi",
    "Remy Rees-Dottin":   "Remy Rees-Dottin",
    "Veljko Milosavljevic": "Veljko Milosavljevic",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Lower-case, strip accents, collapse whitespace."""
    nfkd   = unicodedata.normalize("NFKD", s)
    ascii_ = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[-\s]+", " ", ascii_).strip().lower()


def safe_filename(name: str) -> str:
    """Return lower-case underscore filename (no accents, no special chars)."""
    name = name.strip()
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
    return None


# ── Data-source builders ───────────────────────────────────────────────────────

def build_espn_roster() -> list[dict]:
    """
    Returns list of {display_name, id} dicts for Bournemouth's ESPN roster.
    """
    players = []
    try:
        print("  Fetching ESPN roster (team 349 / eng.1) ...")
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


def build_espn_lookup(roster: list[dict]) -> dict:
    """Returns {normalized_name: espn_player_id}."""
    lookup: dict = {}
    for p in roster:
        lookup[normalize(p["display_name"])] = p["id"]
    return lookup


def build_fpl_lookup() -> dict:
    """
    Returns {normalized_name: fpl_photo_url} for every Bournemouth player in FPL.
    Uses resources.premierleague.com/110x140 which has current-season kit photos.
    """
    lookup: dict = {}
    try:
        print("  Fetching Fantasy Premier League bootstrap ...")
        r = requests.get(FPL_API, headers=HEADERS, timeout=30)
        r.raise_for_status()
        for p in r.json().get("elements", []):
            if p.get("team") != BOURNEMOUTH_FPL_ID:
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


def build_tm_lookup() -> dict:
    """
    Scrapes the Transfermarkt kader page for Bournemouth and returns
    {normalized_name: portrait_url}.  Photos may not be in current Bournemouth
    kit for very recent signings.
    """
    lookup: dict = {}
    try:
        print("  Fetching Transfermarkt squad page ...")
        r = requests.get(TM_KADER_URL, headers=TM_HEADERS, timeout=20)
        r.raise_for_status()
        # Pattern: data-src="https://img.a.transfermarkt.technology/portrait/medium/..."  alt="Player Name"
        pairs = re.findall(
            r'data-src=["\']([^"\']*transfermarkt[^"\']*portrait/medium/[^"\']+)["\'][^>]*?alt=["\']([^"\']+)["\']',
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


# ── FPL lookup with name resolution ───────────────────────────────────────────

def fpl_url_for(espn_display_name: str, fpl_lookup: dict) -> str | None:
    """
    Try to resolve an ESPN display name to a FPL photo URL.
    Applies ESPN_TO_FPL_NAME overrides, then fuzzy-matches.
    Verifies the URL returns a real image (HTTP 200, >5 KB).
    """
    candidates = {espn_display_name}
    override = ESPN_TO_FPL_NAME.get(espn_display_name)
    if override:
        candidates.add(override)

    for name in candidates:
        key     = normalize(name)
        matched = _squad_match(key, fpl_lookup)
        if matched:
            url = fpl_lookup[matched]
            try:
                r = requests.head(url, headers=HEADERS, timeout=10)
                if r.status_code == 200:
                    return url
            except Exception:
                pass
    return None


def tm_url_for(espn_display_name: str, tm_lookup: dict) -> str | None:
    """
    Try to resolve an ESPN display name to a Transfermarkt portrait URL.
    Applies ESPN_TO_FPL_NAME overrides for common name variants.
    Verifies the URL returns a real image.
    """
    candidates = {espn_display_name}
    override = ESPN_TO_FPL_NAME.get(espn_display_name)
    if override:
        candidates.add(override)

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

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("  AFC Bournemouth — Player Headshot Scraper")
    print("=" * 60)
    print(f"  Output folder: {OUTPUT_DIR}\n")

    # Build lookups
    espn_roster  = build_espn_roster()
    espn_lookup  = build_espn_lookup(espn_roster)
    fpl_lookup   = build_fpl_lookup()
    tm_lookup    = build_tm_lookup()

    print(f"\n  ESPN players   : {len(espn_roster)}")
    print(f"  FPL entries    : {len(fpl_lookup)}")
    print(f"  TM entries     : {len(tm_lookup)}")
    print()
    print("-" * 60)
    print("Downloading headshots ...\n")

    results  = {"downloaded": 0, "skipped": 0, "no_image": 0}
    total    = len(espn_roster)
    missing  = []

    for i, player in enumerate(espn_roster, 1):
        dname = player["display_name"]
        fpath = OUTPUT_DIR / (safe_filename(dname) + ".png")

        print(f"  [{i:>2}/{total}] {dname}")

        if fpath.exists():
            print("           Already exists — skipped")
            results["skipped"] += 1
            continue

        img_url: str | None = None
        source: str         = ""

        # ── 1. FPL CDN ────────────────────────────────────────────────────
        url = fpl_url_for(dname, fpl_lookup)
        if url:
            img_url = url
            source  = "FPL"

        # ── 2. Transfermarkt portrait ─────────────────────────────────────
        if not img_url:
            url = tm_url_for(dname, tm_lookup)
            if url:
                img_url = url
                source  = "TM"

        # ── 3. ESPN CDN ───────────────────────────────────────────────────
        if not img_url:
            espn_id  = espn_lookup.get(normalize(dname))
            if espn_id:
                espn_url = ESPN_HEADSHOT.format(id=espn_id)
                try:
                    r = requests.head(espn_url, headers=HEADERS, timeout=10)
                    if r.status_code == 200:
                        img_url = espn_url
                        source  = "ESPN"
                except Exception:
                    pass

        # ── Save ──────────────────────────────────────────────────────────
        if img_url:
            hdrs     = TM_HEADERS if source == "TM" else HEADERS
            min_sz   = 1000 if source == "TM" else 5000  # TM portraits can be ~3 KB
            ok       = download_image(img_url, fpath, hdrs, min_sz)
            if ok:
                tm_note = " [portrait — may not be AFCB kit]" if source == "TM" else ""
                print(f"           [{source}]{tm_note} Saved → {fpath.name}")
                results["downloaded"] += 1
            else:
                print(f"           Download failed for {img_url}")
                results["no_image"] += 1
                missing.append(dname)
        else:
            print("           No image found in any source")
            results["no_image"] += 1
            missing.append(dname)

        time.sleep(0.25)

    print("\n" + "=" * 60)
    print(f"  Downloaded : {results['downloaded']}")
    print(f"  Skipped    : {results['skipped']}  (already existed)")
    print(f"  No image   : {results['no_image']}")
    if missing:
        print("\n  Players with no image found:")
        for m in missing:
            print(f"    - {m}")
    print("=" * 60)


if __name__ == "__main__":
    main()
