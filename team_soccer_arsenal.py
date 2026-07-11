"""
Arsenal FC - Player Headshot Scraper (Soccer / EPL)
Downloads headshots for a specific list of Arsenal players.

Sources (tried in order per player):
  1. ESPN CDN  — fetched via the ESPN soccer roster API (team 359 / eng.1)
                 and ESPN player-search API for any unmatched names.
  2. FPL CDN   — https://resources.premierleague.com (250x250 PNGs)
                 via the Fantasy Premier League bootstrap API (team 1).

URL reference: https://www.espn.com/soccer/team/squad/_/id/359/eng.arsenal
"""

import re
import time
import unicodedata
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ESPN_ROSTER_API = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/359/roster"
)
ESPN_SEARCH_API = (
    "https://site.api.espn.com/apis/common/v3/search"
)
ESPN_HEADSHOT   = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

FPL_API         = "https://fantasy.premierleague.com/api/bootstrap-static/"
PL_PHOTO_CDN    = "https://resources.premierleague.com/premierleague/photos/players/250x250/p{code}.png"
ARSENAL_FPL_ID  = 1

OUTPUT_DIR = Path("f:/logo/arsenal_soccer_player_logos")

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
    "Aleksandr Frantsuzov",
    "Aleksandr Mikhalenko",
    "Aleksandr Skshinetskiy",
    "Alexei Rojas Fedorushchenko",
    "Andre Annous",
    "Andrey Ishutin",
    "Artem Soroko",
    "Artem Vashchenko",
    "Ben White",
    "Bukayo Saka",
    "Charles Sagoe Jr",
    "Christian Nørgaard",
    "Cristhian Mosquera",
    "David Raya",
    "Declan Rice",
    "Dmitri Lutik",
    "Dmitriy Vashkevich",
    "Eberechi Eze",
    "Eduard Akunets",
    "Ethan Nwaneri",
    "Fatkhullo Olimzoda",
    "Gabriel Fernando de Jesus",
    "Gabriel Teodoro Martinelli Silva",
    "Gabriel dos Santos Magalhães",
    "Gleb Prigodsky",
    "Ivan Oreshkevich",
    "Ivan Sanko",
    "Jurriën Timber",
    "Kai Havertz",
    "Kepa Arrizabalaga Revuelta",
    "Kirill Volkov",
    "Leandro Trossard",
    "Maksim Gaevoy",
    "Mark Mokin",
    "Marli Salmon",
    "Martin Ødegaard",
    "Martín Zubimendi",
    "Matvey Mikhayrin",
    "Max Dowman",
    "Mikel Merino",
    "Mikhail Shchetinin",
    "Myles Lewis-Skelly",
    "Nikita Kaplenko",
    "Nikita Vlasenko",
    "Nikolay Sotnikov",
    "Noni Madueke",
    "Piero Hincapié",
    "Riccardo Calafiori",
    "Roman Vegerya",
    "Ruslan Myalkovskiy",
    "Tommy Setford",
    "Vadim Harutyunyan",
    "Valeri Senko",
    "Viktor Gyökeres",
    "Vladislav Vasilyev",
    "William Saliba",
    "Yuri Lovets",
]

# Short/common names ESPN may use — maps TARGET_PLAYERS name → ESPN display name
ESPN_NAME_OVERRIDES = {
    "Gabriel Fernando de Jesus":         "Gabriel Jesus",
    "Gabriel Teodoro Martinelli Silva":  "Gabriel Martinelli",
    "Gabriel dos Santos Magalhães":      "Gabriel Magalhães",
    "Kepa Arrizabalaga Revuelta":        "Kepa",
    "Jurriën Timber":                    "Jurrien Timber",
    "Martín Zubimendi":                  "Martin Zubimendi",
    "Piero Hincapié":                    "Piero Hincapie",
    "Viktor Gyökeres":                   "Viktor Gyokeres",
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def normalize(s: str) -> str:
    """Lower-case, strip accents, collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", s)
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


# ── Data sources ───────────────────────────────────────────────────────────────

def build_espn_lookup() -> dict[str, str]:
    """
    Returns {normalized_name: espn_player_id} for every player
    in Arsenal's ESPN soccer roster (team 359).
    The API response uses a top-level 'athletes' list (not roster.entries).
    """
    lookup: dict[str, str] = {}
    try:
        print("  Fetching ESPN roster (team 359 / eng.1) ...")
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


def espn_search(name: str) -> str | None:
    """Search ESPN for a player by name; return player ID or None."""
    try:
        params = {"query": name, "sport": "soccer", "limit": "5", "type": "player"}
        r = requests.get(ESPN_SEARCH_API, params=params, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        results = r.json().get("results", [])
        for item in results:
            # Each item: {"type": "player", "displayName": ..., "id": ...}
            if item.get("type") == "player":
                norm_result = normalize(item.get("displayName", ""))
                norm_query  = normalize(name)
                # Accept if query words are a subset of result words
                q_words = set(norm_query.split())
                r_words = set(norm_result.split())
                if q_words & r_words and len(q_words & r_words) >= min(2, len(q_words)):
                    uid = item.get("id") or item.get("uid", "")
                    # uid may look like "s:600~a:12345" — extract digits
                    m = re.search(r"a:(\d+)", str(uid))
                    if m:
                        return m.group(1)
                    if str(uid).isdigit():
                        return str(uid)
    except Exception:
        pass
    return None


def build_fpl_lookup() -> dict[str, str]:
    """
    Returns {normalized_name: photo_url} for every Arsenal player in FPL.
    """
    lookup: dict[str, str] = {}
    try:
        print("  Fetching Fantasy Premier League bootstrap ...")
        r = requests.get(FPL_API, headers=HEADERS, timeout=20)
        r.raise_for_status()
        data = r.json()
        for p in data.get("elements", []):
            if p.get("team") != ARSENAL_FPL_ID:
                continue
            code  = p.get("code", "")
            first = p.get("first_name", "")
            last  = p.get("second_name", "")
            full  = f"{first} {last}".strip()
            if full and code:
                url = PL_PHOTO_CDN.format(code=code)
                lookup[normalize(full)] = url
    except Exception as e:
        print(f"  WARNING  FPL fetch failed: {e}")
    return lookup


def _squad_match(key: str, roster: dict[str, str]) -> str | None:
    """
    Try to match a normalized player name against a roster dict.
    Returns the roster key on success, else None.

    Accepts:
    - Exact match, OR
    - 2+ words in common  (handles long legal names vs short display names), OR
    - Shared last word AND at least 1 word in common  (handles Ben vs Benjamin)
    """
    if key in roster:
        return key
    words     = key.split()
    last_word = words[-1]
    word_set  = set(words)
    for rk in roster:
        rw      = rk.split()
        common  = word_set & set(rw)
        if len(common) >= 2:
            return rk
        if rw[-1] == last_word and len(common) >= 1:
            return rk
    return None


def is_in_squad(player_name: str,
               espn_lookup: dict[str, str],
               fpl_lookup: dict[str, str]) -> bool:
    """
    Return True if the player can be matched to either the ESPN or FPL
    Arsenal squad roster. Checks both the full legal name supplied and
    any short/display-name override, so every form is covered.
    """
    # Build candidate keys: always check the original name; also the override
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
    print("  Arsenal FC — Player Headshot Scraper")
    print("=" * 60)
    print(f"  Players to download : {len(TARGET_PLAYERS)}")
    print(f"  Output folder       : {OUTPUT_DIR}\n")

    espn_lookup = build_espn_lookup()
    fpl_lookup  = build_fpl_lookup()
    print(f"\n  ESPN roster entries : {len(espn_lookup)}")
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
        if not is_in_squad(player_name, espn_lookup, fpl_lookup):
            print(f"           Not in Arsenal squad — skipped")
            results["not_in_squad"] += 1
            continue

        if fpath.exists():
            print(f"           Already exists — skipped")
            results["skipped"] += 1
            continue

        img_url: str | None = None

        # ── 1. Try ESPN CDN ────────────────────────────────────────────────────
        search_name  = ESPN_NAME_OVERRIDES.get(player_name, player_name)
        espn_key     = normalize(search_name)
        matched_espn = _squad_match(espn_key, espn_lookup)
        # also try the original name if override didn't match
        if not matched_espn and search_name != player_name:
            matched_espn = _squad_match(normalize(player_name), espn_lookup)
        espn_id = espn_lookup[matched_espn] if matched_espn else None

        # fall back to live ESPN search
        if not espn_id:
            espn_id = espn_search(search_name)
            if espn_id:
                print(f"           (ESPN search hit: id={espn_id})")

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
            fpl_key = normalize(player_name)
            # try full name; then 2-word intersection for legal-vs-display mismatches
            matched_key = _squad_match(fpl_key, fpl_lookup)
            fpl_url = fpl_lookup[matched_key] if matched_key else None
            if fpl_url:
                try:
                    r = requests.get(fpl_url, headers=HEADERS, timeout=15)
                    if r.status_code == 200 and len(r.content) > 1000:
                        img_url = fpl_url
                except Exception:
                    pass

        # ── Download or report ─────────────────────────────────────────────────
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
    print(f"    Not in squad   : {results['not_in_squad']}  (not on Arsenal roster)")
    print(f"    No image found : {results['no_image']}")
    print(f"  Output folder: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
