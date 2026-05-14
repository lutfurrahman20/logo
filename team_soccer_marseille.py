"""
Olympique de Marseille — Player Headshot Downloader (Soccer / Ligue 1)

Sources (tried in order per player):
  1. OM.fr Official   — https://www.om.fr/fr/equipe/hommes/{slug}
                        Player portrait: Sanity CDN PNG extracted from Next.js RSC payload
                        Typical size: ~488x825 px PNG (~150–400KB)
  2. Wikipedia        — en.wikipedia.org pageimages API (article thumbnail)
  3. Transfermarkt    — portrait photos (verein/244)
  4. ESPN CDN         — a.espncdn.com (sparse for Ligue 1, last resort)

Squad sourced from:
  https://www.espn.com/soccer/team/squad/_/id/176/marseille
"""

import difflib
import io
import re
import time
import unicodedata
import requests
from pathlib import Path
from PIL import Image

# ── Config ────────────────────────────────────────────────────────────────────
ESPN_ROSTER_API = "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/teams/176/roster"
ESPN_HEADSHOT   = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

OM_SITEMAP_URL  = "https://www.om.fr/sitemaps/players"
OM_PLAYER_BASE  = "https://www.om.fr/fr/equipe/hommes/{slug}"

TM_KADER_URL    = "https://www.transfermarkt.com/olympique-marseille/kader/verein/244"
WP_API          = "https://en.wikipedia.org/w/api.php"

OUTPUT_DIR = Path("f:/logo/marseille_soccer_player_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
TM_HEADERS = {**HEADERS, "Referer": "https://www.transfermarkt.com/"}
OM_HEADERS = {**HEADERS, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}
WP_HEADERS = {"User-Agent": "logo-collector/1.0 (educational)"}

# ── Target player list (36 players from ESPN squad page) ─────────────────────
TARGET_PLAYERS = [
    "Amine Gouiri",
    "Amir Murillo",
    "Ange Lago",
    "Angel Gomes",
    "Arthur Vermeeren",
    "Benjamin Pavard",
    "Bilal Nadir",
    "CJ Egan-Riley",
    "Darryl Bakola",
    "Emerson Palmieri dos Santos",
    "Facundo Medina",
    "Geoffrey Kondogbia",
    "Gerónimo Rulli",
    "Hamed Traorè",
    "Igor Guilherme Barbosa da Paixão",
    "Jeffrey de Lange",
    "Jelle Van Neck",
    "Keyliane Abdallah",
    "Leonardo Balerdi",
    "Mason Greenwood",
    "Mathis Clement",
    "Matt O'Riley",
    "Nayef Aguerd",
    "Neal Maupay",
    "Pierre-Emerick Aubameyang",
    "Pierre-Emile Højbjerg",
    "Pladi N'Zinga Pambani",
    "Pol Lirola",
    "Rayan Bang Na",
    "Robinio Vaz",
    "Rubén Blanco",
    "Tadjidine Mmadi",
    "Théo Vermot",
    "Timothy Weah",
    "Ulisses Garcia",
    "Yanis Sellami",
]

# ── Wikipedia title overrides (normalized-name -> exact WP article title) ───────
WP_OVERRIDES: dict[str, str] = {
    "igor guilherme barbosa da paixao": "Igor Paixão",
    "igor paixao":                      "Igor Paixão",
    "pierre-emile hojbjerg":            "Pierre-Emile Højbjerg",
    "pierre emile hojbjerg":            "Pierre-Emile Højbjerg",
    "emerson palmieri dos santos":      "Emerson Palmieri",
    "emerson palmieri":                 "Emerson Palmieri",
    "matt o riley":                     "Matt O'Riley",
    "geronimo rulli":                   "Gerónimo Rulli",
    "hamed traore":                     "Hamed Traoré",
}

# ── Manual slug overrides for tricky names ────────────────────────────────────
# Built from OM.fr sitemap inspection
# OM.fr slugs that return a jersey image instead of a player portrait
OM_SLUG_BLOCKLIST = {
    "jelle-van-neck",   # jersey back image on OM.fr
    "theo-vermot",      # jersey back image on OM.fr
}

SLUG_OVERRIDES = {
    "cj egan-riley":                "conrad-jaden-egan-riley",
    "cj egan riley":                "conrad-jaden-egan-riley",
    "hamed traore":                 "hamed-junior-traore",
    "pierre-emile hojbjerg":        "pierre-emile-h-jbjerg",
    "pierre emile hojbjerg":        "pierre-emile-h-jbjerg",
    "emerson palmieri dos santos":  "emerson-palmieri",
    "emerson palmieri":             "emerson-palmieri",
    "igor guilherme barbosa da paixao": "igor-paixao",
    "igor paixao":                  "igor-paixao",
    "matt o riley":                 "matt-o-riley",
    "matt o'riley":                 "matt-o-riley",
}

# ── Character normalization ───────────────────────────────────────────────────
_CHAR_MAP = str.maketrans({
    "ø": "o", "Ø": "O",
    "æ": "ae", "Æ": "AE",
    "ß": "ss",
    "ł": "l",  "Ł": "L",
    "ı": "i",
    "đ": "d",
    "'": "-", "\u2019": "-",
})


def normalize(s: str) -> str:
    s = s.translate(_CHAR_MAP)
    nfkd   = unicodedata.normalize("NFKD", s)
    ascii_ = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[-\s]+", " ", ascii_).strip().lower()


def to_slug(name: str) -> str:
    """Convert a player display name to an OM.fr URL slug."""
    norm = normalize(name)
    # Check manual overrides first
    if norm in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[norm]
    slug = re.sub(r"[^\w\s-]", "", norm)
    slug = re.sub(r"[\s]+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug


def safe_filename(name: str) -> str:
    name = name.strip().translate(_CHAR_MAP)
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s-]", "", name)
    return re.sub(r"[-\s]+", "_", name).lower()


def download_image(url: str, filepath: Path, hdrs: dict = None, min_size: int = 5000) -> bool:
    try:
        r = requests.get(url, headers=hdrs or HEADERS, timeout=20)
        if r.status_code == 200 and len(r.content) >= min_size:
            # Always save as PNG regardless of source format
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            png_path = filepath.with_suffix(".png")
            img.save(png_path, "PNG")
            return True
    except Exception as e:
        print(f"    ERROR    {e}")
    return False


# ── Data-source builders ──────────────────────────────────────────────────────

def build_espn_roster() -> list[dict]:
    players = []
    try:
        print("  Fetching ESPN roster (team 176 / fra.1) ...")
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


def build_om_slug_set() -> set[str]:
    """Fetch all men's player slugs from OM.fr sitemap."""
    try:
        print("  Fetching OM.fr player sitemap ...")
        r = requests.get(OM_SITEMAP_URL, headers=OM_HEADERS, timeout=15)
        r.raise_for_status()
        slugs = set(re.findall(
            r'<loc>https://www\.om\.fr/fr/equipe/hommes/([^<]+)</loc>',
            r.text,
        ))
        print(f"  OM.fr men slugs: {len(slugs)}")
        return slugs
    except Exception as e:
        print(f"  WARNING  OM.fr sitemap failed: {e}")
        return set()


def slug_for_player(name: str, om_slugs: set[str]) -> str | None:
    """Return the best OM.fr slug for a player name, or None if not found."""
    candidate = to_slug(name)
    if candidate in om_slugs:
        return candidate

    # Try fuzzy match in slug set (handles extra/missing middle names)
    norm  = normalize(name)
    words = [w for w in norm.split() if len(w) >= 3]

    # A slug matches if it contains the last word of the name AND one other word
    # Require at least 2 words to match to avoid false positives like "clement-amiot" for "Mathis Clement"
    if len(words) >= 2:
        last = words[-1]
        first = words[0]
        candidates = [s for s in om_slugs if last in s.split("-") and first in s.split("-")]
        if not candidates:
            # Relax: last name + at least one other word
            candidates = [s for s in om_slugs if last in s.split("-") and
                          sum(1 for w in words if w in s.split("-")) >= 2]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            # Pick slug with most matching words
            best = max(candidates, key=lambda s: sum(1 for w in words if w in s.split("-")))
            return best

    # difflib fallback on full slug
    matches = difflib.get_close_matches(candidate, list(om_slugs), n=1, cutoff=0.72)
    if matches:
        return matches[0]

    return None


OM_PLACEHOLDER_HASH = "ce545ecf8a8eae404f42eabbd4beccb9f44216bb"


def wp_image_for_player(name: str) -> str | None:
    """Return Wikipedia article thumbnail URL for a player, or None."""
    norm     = normalize(name)
    wp_title = WP_OVERRIDES.get(norm, name)
    try:
        r = requests.get(WP_API, params={
            "action":      "query",
            "titles":      wp_title,
            "prop":        "pageimages",
            "format":      "json",
            "pithumbsize": 400,
        }, headers=WP_HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        pages = r.json().get("query", {}).get("pages", {})
        page  = next(iter(pages.values()))
        thumb = page.get("thumbnail", {})
        if thumb and thumb.get("source"):
            return thumb["source"]
    except Exception as e:
        print(f"    Wikipedia error for {name}: {e}")
    return None


def portrait_from_om_page(slug: str) -> str | None:
    """Fetch player page and extract Sanity CDN portrait image URL from RSC payload."""
    url = OM_PLAYER_BASE.format(slug=slug)
    try:
        r = requests.get(url, headers=OM_HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        text = r.text

        # The player portrait appears directly in the HTML as a Sanity CDN image URL.
        # Pattern: cdn.sanity.io/images/2omis1jj/production/{hash}-{W}x{H}.{ext}
        # Filter out: placeholder silhouette hash, landscape images, tiny images.
        imgs = re.findall(
            r'cdn\.sanity\.io/images/2omis1jj/production/'
            r'([a-f0-9]+-(\d+)x(\d+)\.(png|jpg))',
            text,
        )
        seen = set()
        for img_part, w_str, h_str, ext in imgs:
            hash_only = img_part.split("-")[0]
            if hash_only == OM_PLACEHOLDER_HASH or img_part in seen:
                continue
            seen.add(img_part)
            w, h = int(w_str), int(h_str)
            # Portrait-shaped (height > width) and minimum width
            if h >= 1.1 * w and w >= 300:
                return f"https://cdn.sanity.io/images/2omis1jj/production/{img_part}"

    except Exception as e:
        print(f"    OM.fr error for {slug}: {e}")
    return None


# ── om1899.com player IDs ────────────────────────────────────────────────────
# Scraped by iterating https://om1899.com/liste-joueurs.php?lettre=X
OM1899_PHOTO_BASE = "https://om1899.com/images/joueurs/{id}.jpg"
OM1899_HEADERS    = {**HEADERS, "Referer": "https://om1899.com/"}

OM1899_PLAYER_IDS: dict[str, int] = {
    "amine gouiri":                         2544,
    "amir murillo":                         2445,
    "ange lago":                            2420,
    "angel gomes":                          2565,
    "arthur vermeeren":                     2586,
    "benjamin pavard":                      2589,
    "bilal nadir":                          2355,
    "cj egan-riley":                        2562,
    "cj egan riley":                        2562,
    "darryl bakola":                        2491,
    "emerson palmieri dos santos":          2588,
    "emerson palmieri":                     2588,
    "facundo medina":                       2566,
    "geoffrey kondogbia":                   2426,
    "geronimo rulli":                       2510,
    "hamed traore":                         2585,
    "igor guilherme barbosa da paixao":     2575,
    "igor paixao":                          2575,
    "jeffrey de lange":                     2506,
    "jelle van neck":                       2393,
    "keyliane abdallah":                    2455,
    "leonardo balerdi":                     2332,
    "mason greenwood":                      2490,
    "mathis clement":                       2454,
    "matt o riley":                         2590,
    "matt o'riley":                         2590,
    "nayef aguerd":                         2587,
    "neal maupay":                          2515,
    "pierre-emerick aubameyang":            2429,
    "pierre emerick aubameyang":            2429,
    "pierre-emile hojbjerg":               2493,
    "pierre emile hojbjerg":               2493,
    "pladi n zinga pambani":               2571,
    "pladi n'zinga pambani":               2571,
    "pol lirola":                           2349,
    "rayan bang na":                        2561,
    "robinio vaz":                          2513,
    "ruben blanco":                         2401,
    "tadjidine mmadi":                      2547,
    "theo vermot":                          2488,
    "timothy weah":                         2577,
    "ulisses garcia":                       2463,
    "yanis sellami":                        2492,
}


def om1899_image_for_player(name: str) -> str | None:
    """Return om1899.com JPEG portrait URL for a player, or None if ID unknown."""
    norm  = normalize(name)
    om_id = OM1899_PLAYER_IDS.get(norm)
    if om_id is None:
        return None
    return OM1899_PHOTO_BASE.format(id=om_id)


# ── Transfermarkt player IDs (spieler IDs for profile-page image lookup) ────
# Discovered via https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche
TM_PLAYER_IDS: dict[str, int] = {
    "amir murillo":                         354482,
    "ange lago":                            1117771,
    "darryl bakola":                        1170286,
    "mathis clement":                       940997,
    "pladi n zinga pambani":               1131155,
    "pladi n'zinga pambani":               1131155,
    "rayan bang na":                        1208712,
    "ruben blanco":                         199321,
    "pierre-emile hojbjerg":               294381,
    "pierre emile hojbjerg":               294381,
    "pierre-emerick aubameyang":           138807,
    "emerson palmieri dos santos":         311486,
    "emerson palmieri":                    311486,
}

# Minimum image bytes for a real portrait (TM default silhouette is 5036B)
_TM_MIN_BYTES = 6000


def tm_profile_image(name: str) -> str | None:
    """Fetch a player portrait from Transfermarkt profile og:image meta tag."""
    norm = normalize(name)
    tm_id = TM_PLAYER_IDS.get(norm)
    if tm_id is None:
        # Fallback: search TM for the player name
        try:
            r = requests.get(
                "https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche",
                params={"query": name},
                headers=TM_HEADERS, timeout=12
            )
            if r.status_code == 200:
                links = re.findall(r'href="/[^"]+/profil/spieler/(\d+)"', r.text)
                if links:
                    tm_id = int(links[0])
        except Exception:
            return None
    if tm_id is None:
        return None

    try:
        r = requests.get(
            f"https://www.transfermarkt.com/x/profil/spieler/{tm_id}",
            headers=TM_HEADERS, timeout=15
        )
        if r.status_code == 200:
            m = re.search(r'og:image[^>]*content="([^"]+)"', r.text)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


def build_tm_lookup() -> dict:
    """Kept for backward compat; returns empty dict (kader scraping is blocked)."""
    print("  Transfermarkt: using profile-page og:image approach")
    return {}


def tm_url_for(name: str, tm_lookup: dict) -> str | None:
    return None  # legacy; replaced by tm_profile_image()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 62)
    print("  Olympique de Marseille — Player Headshot Scraper")
    print("=" * 62)

    espn_roster = build_espn_roster()
    om_slugs    = build_om_slug_set()
    tm_lookup   = build_tm_lookup()

    # ESPN id map
    espn_id_map: dict[str, str] = {}
    for p in espn_roster:
        espn_id_map[normalize(p["display_name"])] = p["id"]

    print(
        f"\n  ESPN: {len(espn_roster)}  OM.fr slugs: {len(om_slugs)}"
        f"  Target: {len(TARGET_PLAYERS)}"
        f"\n  Output: {OUTPUT_DIR}\n" + "-" * 62
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

        # Source 1: OM.fr official portrait
        slug = slug_for_player(name, om_slugs)
        if slug and slug not in OM_SLUG_BLOCKLIST:
            portrait_url = portrait_from_om_page(slug)
            if portrait_url and download_image(portrait_url, filepath, hdrs=OM_HEADERS, min_size=20000):
                kb = filepath.stat().st_size // 1024
                print(f"           [OM.fr  ] {slug} -> {filename} ({kb}KB)")
                downloaded += 1
                time.sleep(0.4)
                continue
            elif slug:
                print(f"           OM.fr slug found ({slug}) but no portrait extracted")
        else:
            print(f"           No OM.fr slug found")

        # Source 2: om1899.com — official club jersey portraits
        om1899_url = om1899_image_for_player(name)
        if om1899_url:
            if download_image(om1899_url, filepath, hdrs=OM1899_HEADERS, min_size=8000):
                kb = filepath.stat().st_size // 1024
                print(f"           [om1899] id={OM1899_PLAYER_IDS.get(normalize(name))} -> {filename} ({kb}KB)")
                downloaded += 1
                time.sleep(0.3)
                continue
            else:
                print(f"           om1899 ID found but image unavailable/too small")
        else:
            print(f"           No om1899 ID found")

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
