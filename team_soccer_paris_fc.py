"""
Paris FC — Player Headshot Downloader (Soccer / Ligue 1)

Sources (tried in order per player):
  1. Paris FC Official — parisfc.fr WordPress uploads
                         Pattern: /wp-content/uploads/{year}/{month}/{number}-{SURNAME}.{ext}
                         ~100–400KB PNG/JPG player card photos
  2. Transfermarkt     — portrait photos (verein/10004)
  3. ESPN CDN          — a.espncdn.com (sparse for Ligue 1, last resort)

Squad sourced from:
  https://www.espn.com/soccer/team/squad/_/id/6851/paris-fc
"""

import difflib
import re
import time
import unicodedata
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
ESPN_ROSTER_API  = "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/teams/6851/roster"
ESPN_HEADSHOT    = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

PARISFC_SQUAD_URL = "https://www.parisfc.fr/equipe/joueurs"

TM_KADER_URL     = "https://www.transfermarkt.com/paris-fc/kader/verein/10004"

OUTPUT_DIR = Path("f:/logo/paris_fc_soccer_player_logos")

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
PARISFC_HEADERS = {
    **HEADERS,
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Referer": "https://www.parisfc.fr/",
}

# ── Target player list (29 players from ESPN squad page) ──────────────────────
TARGET_PLAYERS = [
    "Adama Camara",
    "Alimami Gory",
    "Hamari Traoré",
    "Ilan Kebbal",
    "Jean-Philippe Krasso",
    "Jonathan Ikoné",
    "Julien López",
    "Kevin Trapp",
    "Killian Prouchet",
    "Lamine Gueye",
    "Lohann Doucet",
    "Mathieu Cafaro",
    "Maxime Lopez",
    "Moses Simon",
    "Moustapha Mbow",
    "Nhoa Sangui",
    "Nouha Dicko",
    "Obed Nkambadio",
    "Otávio Ataíde da Silva",
    "Pierre Lees-Melou",
    "Pierre-Yves Hamel",
    "Rémy Riou",
    "Samir Chergui",
    "Sofiane Alakouch",
    "Thibault De Smet",
    "Timothée Kolodziejczak",
    "Tuomas Ollila",
    "Vincent Marchetti",
    "Willem Geubbels",
]

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
    nfkd   = unicodedata.normalize("NFKD", s)
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
        print("  Fetching ESPN roster (team 6851 / fra.1) ...")
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


def build_parisfc_lookup() -> dict:
    """
    Returns {slug_keyword: url} where slug_keyword is the normalized surname
    extracted from the WordPress upload filename (e.g. 'riou', 'nkambadio').
    Multiple keywords may map to the same URL.
    """
    lookup: dict = {}
    try:
        print("  Fetching Paris FC official squad page ...")
        r = requests.get(PARISFC_SQUAD_URL, headers=PARISFC_HEADERS, timeout=20)
        r.raise_for_status()
        # Find all player WP upload images (exclude logos/staff/banners)
        # Pattern: /wp-content/uploads/{yr}/{mo}/{jersey}-{SURNAME(-suffix)}.{ext}
        raw_urls = re.findall(
            r"https://parisfc\.fr/wp-content/uploads/\d{4}/\d{2}/[\w\-\.]+\.(?:png|jpg)",
            r.text,
        )
        seen = set()
        for url in raw_urls:
            if url in seen:
                continue
            seen.add(url)
            fname = url.split("/")[-1]
            # Skip obvious non-player files
            if any(x in fname.lower() for x in ["staff", "logo", "banniere", "paris-fc",
                                                  "cropped", "footer", "badge", "adidas",
                                                  "exemple", "munetsi", "matondo", "koleosho",
                                                  "immobile", "coppola", "bejanin", "toru",
                                                  "profil_"]):
                continue
            # Strip jersey number prefix: e.g. "14-traore-1.png" -> "traore-1.png"
            base = re.sub(r"^\d+-", "", fname)
            # Remove extension
            base = re.sub(r"\.(png|jpg|webp)$", "", base, flags=re.I)
            # Normalize: remove digits, hyphens-to-space, lowercase, strip accents
            base = re.sub(r"-\d+$", "", base)   # drop trailing -1, -2 etc.
            base = base.replace("-", " ").replace("_", " ")
            base_norm = normalize(base)
            # Split into individual words as lookup keys
            for word in base_norm.split():
                if len(word) >= 3:
                    lookup[word] = url
            # Also store the full slug as a key
            if base_norm not in lookup:
                lookup[base_norm] = url
        print(f"  Paris FC official entries: {len(lookup)}")
    except Exception as e:
        print(f"  WARNING  Paris FC official failed: {e}")
    return lookup


def parisfc_url_for(player_name: str, pfc_lookup: dict) -> str | None:
    """
    Match a player name to a Paris FC WordPress upload.
    Strategies (in order):
      1. Any word of normalized name is a key in the lookup
      2. A key is a prefix/substring of any word of the normalized name
      3. Any word of normalized name is a prefix of a key
    """
    norm  = normalize(player_name)
    words = norm.split()

    # Remove bare common words that might falsely match
    stop = {"de", "la", "le", "du", "van", "von", "di", "da"}
    words_filtered = [w for w in words if w not in stop]

    # 1. exact word match
    for w in words_filtered:
        if w in pfc_lookup:
            return pfc_lookup[w]

    # 2. lookup key is subst ring of one of player's words (handles abbrevs like LEESMELOU vs lees-melou)
    norm_nospace = norm.replace(" ", "").replace("-", "")
    for key, url in pfc_lookup.items():
        key_nospace = key.replace(" ", "")
        if key_nospace and (key_nospace in norm_nospace or norm_nospace.endswith(key_nospace)):
            return url

    # 3. player word starts with key (handles short-prefix matches)
    for w in words_filtered:
        for key in pfc_lookup:
            if len(key) >= 4 and (w.startswith(key) or key.startswith(w)):
                return pfc_lookup[key]

    # 4. fuzzy match for long words — handles typos/variant spellings on official site
    #    e.g. KOLOZIEJCZAK vs kolodziejczak, OLLILLA vs ollila, sanghi vs sangui
    for w in words_filtered:
        if len(w) < 6:
            continue
        keys_long = [k for k in pfc_lookup if len(k) >= 6]
        matches = difflib.get_close_matches(w, keys_long, n=1, cutoff=0.82)
        if matches:
            return pfc_lookup[matches[0]]

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

    if norm in tm_lookup:
        return tm_lookup[norm]

    for rk in tm_lookup:
        rw = rk.split()
        common = set(words) & set(rw)
        if len(common) >= 2:
            return tm_lookup[rk]

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
    print("  Paris FC — Player Headshot Scraper")
    print("=" * 62)

    espn_roster   = build_espn_roster()
    pfc_lookup    = build_parisfc_lookup()
    tm_lookup     = build_tm_lookup()

    # Build ESPN id map by name
    espn_id_map: dict[str, str] = {}
    for p in espn_roster:
        espn_id_map[normalize(p["display_name"])] = p["id"]

    print(
        f"\n  ESPN: {len(espn_roster)}  Paris FC official: {len(pfc_lookup)}"
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

        # Source 1: Paris FC official WP
        url = parisfc_url_for(name, pfc_lookup)
        if url and download_image(url, filepath, hdrs=PARISFC_HEADERS, min_size=10000):
            print(f"           [PARISFC] Saved → {filename} ({filepath.stat().st_size // 1024}KB)")
            downloaded += 1
            time.sleep(0.3)
            continue

        # Source 2: Transfermarkt
        url = tm_url_for(name, tm_lookup)
        if url and download_image(url, filepath, hdrs=TM_HEADERS, min_size=1000):
            print(f"           [TM     ] Saved → {filename} ({filepath.stat().st_size // 1024}KB)")
            downloaded += 1
            time.sleep(0.3)
            continue

        # Source 3: ESPN CDN (usually 404 for Ligue 1)
        eid = espn_id_map.get(normalize(name))
        if eid:
            url = ESPN_HEADSHOT.format(id=eid)
            if download_image(url, filepath, min_size=5000):
                print(f"           [ESPN   ] Saved → {filename} ({filepath.stat().st_size // 1024}KB)")
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
