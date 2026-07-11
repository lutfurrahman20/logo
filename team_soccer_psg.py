"""
Paris Saint-Germain — Player Headshot Downloader (Soccer / Ligue 1)

Sources (tried in order per player):
  1. PSG Official  — media.psg.fr Cloudinary CDN (card portrait + jersey, PNG ~130-280KB)
                     Extracted from https://www.psg.fr/football-masculin/effectif
  2. Transfermarkt — portrait photos (verein/583)
  3. ESPN CDN      — a.espncdn.com (sparse for Ligue 1, last resort)

Squad sourced from:
  https://www.espn.com/soccer/team/squad/_/id/160/paris-saint-germain
"""

import re
import time
import unicodedata
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ESPN_ROSTER_API  = "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/teams/160/roster"
ESPN_HEADSHOT    = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

PSG_EFFECTIF_URL = "https://www.psg.fr/football-masculin/effectif"
# Cloudinary: change f_avif → f_png, set width 600px
PSG_IMG_TEMPLATE = "https://media.psg.fr/image/upload/c_limit,w_600/f_png/v1/{card_id}"

TM_KADER_URL     = "https://www.transfermarkt.com/paris-saint-germain/kader/verein/583"

OUTPUT_DIR = Path("f:/logo/psg_soccer_player_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
TM_HEADERS = {
    **HEADERS,
    "Referer": "https://www.transfermarkt.com/",
}
PSG_HEADERS = {
    **HEADERS,
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": "https://www.psg.fr/",
}

# ── Target player list (29 players from ESPN squad page) ──────────────────────
TARGET_PLAYERS = [
    "Achraf Hakimi",
    "Bradley Barcola",
    "David Boly",
    "Désiré Doué",
    "Fabián Ruiz",
    "Gonçalo Matias Ramos",
    "Ibrahim Mbaye",
    "Illia Zabarnyi",
    "João Pedro Gonçalves Neves",
    "Kang-In Lee",
    "Khvicha Kvaratskhelia",
    "Lucas Chevalier",
    "Lucas Hernández",
    "Lucas Lopes Beraldo",
    "Marcos Aoás Corrêa",
    "Martin James",
    "Mathis Jangeal",
    "Matvey Safonov",
    "Noham Kamara",
    "Nuno Alexandre Tavares Mendes",
    "Ousmane Dembélé",
    "Quentin Ndjantou",
    "Renato Marin",
    "Senny Mayulu",
    "Vítor Machado Ferreira",
    "Warren Zaïre-Emery",
    "Wassim Slama",
    "Willian Pacho",
    "Yanis Khafi",
]

# ── Known nickname / abbreviated surname mappings for PSG card IDs ─────────────
# card_label (lowercased) → fragment that appears in normalized real name
PSG_CARD_ALIAS: dict[str, str] = {
    "marquinhos": "correa",       # Marcos Aoás Corrêa  
    "vitinha":    "ferreira",     # Vítor Machado Ferreira
    "kvara":      "kvaratskhelia",
    "zaire":      "zaire",        # Zaïre-Emery — hyphen, normalize to "zaire"
}

# ── Character normalization ───────────────────────────────────────────────────
_CHAR_MAP = str.maketrans({
    "ø": "o", "Ø": "O",
    "æ": "ae", "Æ": "AE",
    "ß": "ss",
    "ł": "l",  "Ł": "L",
    "ı": "i",
    "ú": "u",  "ù": "u",  "û": "u",  "ü": "u",
    "á": "a",  "à": "a",  "â": "a",  "ä": "a",
    "é": "e",  "è": "e",  "ê": "e",  "ë": "e",
    "í": "i",  "ï": "i",  "î": "i",
    "ó": "o",  "ô": "o",  "ö": "o",
    "ñ": "n",  "ç": "c",
    "č": "c",  "š": "s",  "ž": "z",
    "ř": "r",  "ě": "e",  "ý": "y",
})


def normalize(s: str) -> str:
    s = s.translate(_CHAR_MAP)
    nfkd  = unicodedata.normalize("NFKD", s)
    ascii_ = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[-\s]+", " ", ascii_).strip().lower()


def safe_filename(name: str) -> str:
    name = name.strip().translate(_CHAR_MAP)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s-]", "", name)
    return re.sub(r"[-\s]+", "_", name).lower()


def download_image(url: str, filepath: Path, hdrs: dict = None, min_size: int = 5000) -> bool:
    try:
        r = requests.get(url, headers=hdrs or HEADERS, timeout=20)
        if r.status_code == 200 and len(r.content) >= min_size:
            filepath.write_bytes(r.content)
            return True
    except Exception as e:
        print(f"    ERROR    {e}")
    return False


# ── Data-source builders ───────────────────────────────────────────────────────

def build_espn_roster() -> list[dict]:
    players = []
    try:
        print("  Fetching ESPN roster (team 160 / fra.1) ...")
        r = requests.get(ESPN_ROSTER_API, headers=HEADERS, timeout=20)
        r.raise_for_status()
        for a in r.json().get("athletes", []):
            pid   = str(a.get("id", ""))
            dname = a.get("displayName", "") or a.get("fullName", "")
            if pid and dname:
                players.append({"display_name": dname, "id": pid})
    except Exception as e:
        print(f"  WARNING  ESPN roster failed: {e}")
    return players


def build_psg_official_lookup() -> dict:
    """
    Returns {card_label: url} where card_label is the lowercased surname
    used in the PSG 2025-26 card image, e.g. 'hakimi', 'kvara', 'marquinhos'.
    """
    lookup: dict = {}
    try:
        print("  Fetching PSG official effectif page ...")
        r = requests.get(PSG_EFFECTIF_URL, headers=PSG_HEADERS, timeout=20)
        r.raise_for_status()
        # Extract unique card identifiers: 2526-Card-{Label}_{cloudinaryId}
        ids = re.findall(
            r"/v\d+/(2526-Card-[A-Za-z0-9_-]+)",
            r.text,
        )
        seen = set()
        for full_id in ids:
            if full_id in seen:
                continue
            seen.add(full_id)
            # label is the part between "Card-" and the "_<cloudinaryId>"
            m = re.match(r"2526-Card-([A-Za-z]+)_([A-Za-z0-9]+)$", full_id)
            if not m:
                continue
            label = m.group(1).lower()
            url   = PSG_IMG_TEMPLATE.format(card_id=full_id)
            lookup[label] = url
        print(f"  PSG official entries: {len(lookup)}")
    except Exception as e:
        print(f"  WARNING  PSG official failed: {e}")
    return lookup


def psg_url_for(player_name: str, psg_lookup: dict) -> str | None:
    """
    Match a player name to a PSG card label.
    Strategies (in order):
      1. Last normalized word = card label            (e.g. 'hakimi')
      2. Any word of player name = card label         (e.g. 'lee', 'ramos')
      3. Card label is a prefix/substring of any word (e.g. 'kvara' ⊆ 'kvaratskhelia')
      4. Alias dict (e.g. 'marquinhos' → 'correa')
    """
    norm   = normalize(player_name)
    words  = norm.split()
    wset   = set(words)

    # 1. exact last word
    last = words[-1]
    if last in psg_lookup:
        return psg_lookup[last]

    # 2. any word exact match
    for w in words:
        if w in psg_lookup:
            return psg_lookup[w]

    # 3. card label is a prefix of any word in player name
    for label, url in psg_lookup.items():
        for w in words:
            if w.startswith(label) or label.startswith(w):
                return url

    # 4. alias dict: card label known alias maps to fragment in player name
    for label, url in psg_lookup.items():
        alias_fragment = PSG_CARD_ALIAS.get(label)
        if alias_fragment and alias_fragment in norm:
            return url

    return None


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
        print(f"  WARNING  Transfermarkt failed: {e}")
    return lookup


def tm_url_for(name: str, tm_lookup: dict) -> str | None:
    norm  = normalize(name)
    words = norm.split()
    last  = words[-1]

    # exact
    if norm in tm_lookup:
        return tm_lookup[norm]

    # 2+ shared words
    for rk in tm_lookup:
        rw = rk.split()
        common = set(words) & set(rw)
        if len(common) >= 2:
            return tm_lookup[rk]

    # same last word + 1 shared word
    for rk in tm_lookup:
        rw = rk.split()
        common = set(words) & set(rw)
        if rw and rw[-1] == last and len(common) >= 1:
            return tm_lookup[rk]

    return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 62)
    print("  Paris Saint-Germain — Player Headshot Scraper")
    print("=" * 62)

    espn_roster  = build_espn_roster()
    psg_lookup   = build_psg_official_lookup()
    tm_lookup    = build_tm_lookup()

    # Build ESPN id map by name (for ESPN CDN fallback)
    espn_id_map: dict[str, str] = {}
    for p in espn_roster:
        espn_id_map[normalize(p["display_name"])] = p["id"]

    print(
        f"\n  ESPN: {len(espn_roster)}  PSG official: {len(psg_lookup)}"
        f"  TM: {len(tm_lookup)}  Target: {len(TARGET_PLAYERS)}"
        f"  Output: {OUTPUT_DIR}\n" + "-" * 62
    )

    downloaded, skipped, no_image = 0, 0, []

    for i, name in enumerate(TARGET_PLAYERS, 1):
        filename = safe_filename(name) + ".png"
        filepath = OUTPUT_DIR / filename
        print(f"  [{i:>2}/{len(TARGET_PLAYERS)}] {name}")

        if filepath.exists():
            print(f"           Already exists — skipped")
            skipped += 1
            continue

        # Source 1: PSG official Cloudinary card
        url = psg_url_for(name, psg_lookup)
        if url and download_image(url, filepath, hdrs=PSG_HEADERS, min_size=30000):
            print(f"           [PSG   ] Saved → {filename} ({filepath.stat().st_size // 1024}KB)")
            downloaded += 1
            time.sleep(0.3)
            continue

        # Source 2: Transfermarkt
        url = tm_url_for(name, tm_lookup)
        if url and download_image(url, filepath, hdrs=TM_HEADERS, min_size=1000):
            print(f"           [TM    ] Saved → {filename} ({filepath.stat().st_size // 1024}KB)")
            downloaded += 1
            time.sleep(0.3)
            continue

        # Source 3: ESPN CDN (usually 404 for Ligue 1, last resort)
        eid = espn_id_map.get(normalize(name))
        if eid:
            url = ESPN_HEADSHOT.format(id=eid)
            if download_image(url, filepath, min_size=5000):
                print(f"           [ESPN  ] Saved → {filename} ({filepath.stat().st_size // 1024}KB)")
                downloaded += 1
                time.sleep(0.3)
                continue

        print(f"           No image found")
        no_image.append(name)

    print(f"\n{'=' * 62}")
    print(f"  Downloaded : {downloaded}")
    print(f"  Skipped    : {skipped}")
    print(f"  No image   : {len(no_image)}")
    for n in no_image:
        print(f"    - {n}")
    print(f"  Output     : {OUTPUT_DIR}")
    print(f"{'=' * 62}")


if __name__ == "__main__":
    main()
