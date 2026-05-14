"""
Aston Villa FC - Player Headshot Scraper (Soccer / EPL)
Downloads headshots for players currently on Aston Villa's squad.

Sources (tried in order per player):
  1. ESPN CDN  — via ESPN soccer roster API (team 362 / eng.1)
  2. FPL CDN   — https://resources.premierleague.com (250x250 PNGs)
                 via the Fantasy Premier League bootstrap API (team 2)

URL reference: https://www.espn.com/soccer/team/squad/_/id/362/aston-villa
"""

import re
import time
import unicodedata
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ESPN_ROSTER_API = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/362/roster"
)
ESPN_HEADSHOT  = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

FPL_API        = "https://fantasy.premierleague.com/api/bootstrap-static/"
PL_PHOTO_CDN   = "https://resources.premierleague.com/premierleague/photos/players/250x250/p{code}.png"
VILLA_FPL_ID   = 2   # Aston Villa's team ID in the FPL API

OUTPUT_DIR = Path("f:/logo/aston_villa_soccer_player_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}
# ───────────────────────────────────────────────────────────────────────────────

# Short/common names ESPN may use — maps full legal name → ESPN display name
ESPN_NAME_OVERRIDES = {
    "Emiliano Martínez Romero":              "Emiliano Martínez",
    "Emiliano Buendía Stati":                "Emiliano Buendía",
    "Ezri Konsa Ngoyo":                      "Ezri Konsa",
    "Álex Moreno Lopera":                    "Álex Moreno",
    "Alysson Edward Franco da Rocha dos Santos": "Alysson",
    "Douglas Luiz Soares de Paulo":          "Douglas Luiz",
    "Victor Lindelöf":                       "Victor Lindelof",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Lower-case, strip accents, collapse whitespace."""
    nfkd   = unicodedata.normalize("NFKD", s)
    ascii_ = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_).strip().lower()


def safe_filename(name: str) -> str:
    name = name.strip()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name.lower()


def download_image(url: str, filepath: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 1000:
            filepath.write_bytes(r.content)
            return True
    except Exception as e:
        print(f"    ERROR    {e}")
    return False


def _squad_match(key: str, roster: dict) -> str | None:
    """
    Match a normalized name against roster keys.
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

def build_espn_lookup() -> dict:
    """
    Returns {normalized_name: espn_player_id} for every player
    in Aston Villa's ESPN soccer roster (team 362).
    """
    lookup: dict = {}
    try:
        print("  Fetching ESPN roster (team 362 / eng.1) ...")
        r = requests.get(ESPN_ROSTER_API, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        for athlete in data.get("athletes", []):
            pid  = str(athlete.get("id", ""))
            full = athlete.get("fullName", "")
            disp = athlete.get("displayName", "")
            for n in (full, disp):
                if n and pid:
                    lookup[normalize(n)] = pid
    except Exception as e:
        print(f"  WARNING  ESPN roster fetch failed: {e}")
    return lookup


def build_fpl_lookup() -> dict:
    """
    Returns {normalized_name: photo_url} for every Aston Villa player in FPL.
    """
    lookup: dict = {}
    try:
        print("  Fetching Fantasy Premier League bootstrap ...")
        r = requests.get(FPL_API, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        for p in data.get("elements", []):
            if p.get("team") != VILLA_FPL_ID:
                continue
            code  = p.get("code", "")
            first = p.get("first_name", "")
            last  = p.get("second_name", "")
            full  = f"{first} {last}".strip()
            if full and code:
                lookup[normalize(full)] = PL_PHOTO_CDN.format(code=code)
    except Exception as e:
        print(f"  WARNING  FPL fetch failed: {e}")
    return lookup


def is_in_squad(player_name: str, espn_lookup: dict, fpl_lookup: dict) -> bool:
    """Return True if the player is on Aston Villa's roster in ESPN or FPL."""
    candidates = {normalize(player_name)}
    override = ESPN_NAME_OVERRIDES.get(player_name)
    if override:
        candidates.add(normalize(override))
    for key in candidates:
        if _squad_match(key, espn_lookup) or _squad_match(key, fpl_lookup):
            return True
    return False


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("  Aston Villa FC — Player Headshot Scraper")
    print("=" * 60)
    print(f"  Output folder : {OUTPUT_DIR}\n")

    espn_lookup = build_espn_lookup()
    fpl_lookup  = build_fpl_lookup()
    print(f"\n  ESPN roster entries : {len(espn_lookup)}")
    print(f"  FPL roster entries  : {len(fpl_lookup)}\n")

    # Build the full player list from both rosters (union, deduped).
    # ESPN display names take priority; FPL entries are only added when they
    # cannot be matched (by _squad_match) to any ESPN name already in the list.
    all_names: list[str] = []
    seen_keys: list[str] = []   # normalized keys already added

    # ESPN names first
    try:
        r = requests.get(ESPN_ROSTER_API, headers=HEADERS, timeout=20)
        data = r.json()
        for athlete in data.get("athletes", []):
            full = athlete.get("fullName", "")
            if full and normalize(full) not in seen_keys:
                all_names.append(full)
                seen_keys.append(normalize(full))
    except Exception:
        pass

    # Add FPL players that have no ESPN equivalent
    for norm_key in fpl_lookup:
        # Build a temporary dict of already-seen keys to run _squad_match against
        already = {k: True for k in seen_keys}
        if _squad_match(norm_key, already) is None:
            all_names.append(norm_key.title())
            seen_keys.append(norm_key)

    print(f"  Total squad players : {len(all_names)}")
    print("-" * 60)
    print("Downloading headshots ...\n")

    results = {"downloaded": 0, "skipped": 0, "no_image": 0}
    total   = len(all_names)

    for i, player_name in enumerate(all_names, 1):
        fname = safe_filename(player_name) + ".png"
        fpath = OUTPUT_DIR / fname

        print(f"  [{i:>2}/{total}] {player_name}")

        if fpath.exists():
            print(f"           Already exists — skipped")
            results["skipped"] += 1
            continue

        img_url: str | None = None

        # ── 1. Try ESPN CDN ────────────────────────────────────────────────────
        search_name  = ESPN_NAME_OVERRIDES.get(player_name, player_name)
        espn_key     = normalize(search_name)
        matched_espn = _squad_match(espn_key, espn_lookup)
        if not matched_espn and search_name != player_name:
            matched_espn = _squad_match(normalize(player_name), espn_lookup)
        espn_id = espn_lookup.get(matched_espn) if matched_espn else None

        if espn_id:
            candidate = ESPN_HEADSHOT.format(id=espn_id)
            try:
                r = requests.get(candidate, headers=HEADERS, timeout=15)
                if r.status_code == 200 and len(r.content) > 1000:
                    img_url = candidate
            except Exception:
                pass

        # ── 2. Fall back to FPL CDN ────────────────────────────────────────────
        if not img_url:
            fpl_key     = normalize(player_name)
            matched_fpl = _squad_match(fpl_key, fpl_lookup)
            # also try override name
            if not matched_fpl:
                override = ESPN_NAME_OVERRIDES.get(player_name)
                if override:
                    matched_fpl = _squad_match(normalize(override), fpl_lookup)
            fpl_url = fpl_lookup.get(matched_fpl) if matched_fpl else None
            if fpl_url:
                try:
                    r = requests.get(fpl_url, headers=HEADERS, timeout=15)
                    if r.status_code == 200 and len(r.content) > 1000:
                        img_url = fpl_url
                except Exception:
                    pass

        # ── Save or report ─────────────────────────────────────────────────────
        if img_url:
            ok = download_image(img_url, fpath)
            if ok:
                source = "ESPN" if "espncdn" in img_url else "FPL"
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
    print(f"    No image found : {results['no_image']}")
    print(f"  Output folder: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
