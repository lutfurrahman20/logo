"""
FC Nantes — Player Headshot Downloader (Soccer / Ligue 1)

Sources (tried in order per player):
  1. FC Nantes Official  — https://www.fcnantes.com/groupepro/20252026/fiche.php?numjoueur={id}
                          Illustration images at: /images/joueurs/20252026/illu200x120/{surname}.png
  2. Wikipedia           — en.wikipedia.org pageimages API (article thumbnail)
  3. ESPN CDN            — a.espncdn.com (sparse for Ligue 1, last resort)

Squad sourced from:
  https://www.espn.com/soccer/team/squad/_/id/165/nantes
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
ESPN_ROSTER_API = "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/teams/165/roster"
NANTES_EFFECTIF = "https://www.fcnantes.com/effectif"
NANTES_PLAYER_PAGE = "https://www.fcnantes.com/groupepro/20252026/fiche.php?numjoueur={id}"
NANTES_IMG_BASE = "https://www.fcnantes.com/images/joueurs/20252026/illu200x120/{surname}.png"
NANTES_IMG_BOUTIQUE = "https://www.fcnantes.com/images/joueurs/20252026/boutique/{surname}.jpg"

WP_API = "https://en.wikipedia.org/w/api.php"
ESPN_HEADSHOT = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

OUTPUT_DIR = Path("f:/logo/nantes_soccer_player_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
NANTES_HEADERS = {**HEADERS, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}
WP_HEADERS = {"User-Agent": "logo-collector/1.0 (educational)"}

# ── Target player list (27 players requested) ─────────────────────────────────
TARGET_PLAYERS = [
    "Adel Mahamoud",
    "Alexis Mirbach",
    "Amady Camara",
    "Anthony Lopes",
    "Bahereba Guirassy",
    "Bahmed Deuff",
    "Chidozie Awaziem",
    "Dehmaine Assoumani",
    "Fabien Centonze",
    "Francis Coquelin",
    "Hyeok-Kyu Kwon",
    "Hyun-Seok Hong",
    "Johann Lepenant",
    "Junior Mwanga",
    "Kelvin Amian",
    "Louis Leroux",
    "Matthis Abline",
    "Mayckel Lahdo",
    "Mostafa Mohamed Ahmed Abdalla",
    "Nicolas Cozza",
    "Patrik Carlgren",
    "Sacha Ziani",
    "Sékou Doucouré",
    "Tylel Tati",
    "Uroš Radaković",
    "Yassine Benhattab",
    "Youssef El Arabi",
]

# ── Wikipedia title overrides ────────────────────────────────────────────────────
WP_OVERRIDES: dict[str, str] = {
    "patrick carlgren": "Patrik Carlgren",
    "francis coquelin": "Francis Coquelin",
    "dehmaine assoumani": "Dehmaine Tabibou",
}

# ── Character normalization ───────────────────────────────────────────────────
_CHAR_MAP = str.maketrans({
    "ø": "o", "Ø": "O",
    "æ": "ae", "Æ": "AE",
    "ß": "ss",
    "ł": "l",  "Ł": "L",
    "ı": "i",
    "đ": "d",
    "š": "s", "Š": "S",
    "ř": "r", "Ř": "R",
    "á": "a", "Á": "A",
    "é": "e", "É": "E",
    "ö": "o", "Ö": "O",
    "ú": "u", "Ú": "U",
    "ü": "u", "Ü": "U",
    "'": "-", "\u2019": "-",
})


def normalize(s: str) -> str:
    s = s.translate(_CHAR_MAP)
    nfkd = unicodedata.normalize("NFKD", s)
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
        print("  Fetching ESPN roster (team 165 / fra.1) ...")
        r = requests.get(ESPN_ROSTER_API, headers=HEADERS, timeout=20)
        r.raise_for_status()
        for a in r.json().get("athletes", []):
            pid = str(a.get("id", ""))
            dname = a.get("displayName", "") or a.get("fullName", "")
            if pid and dname:
                players.append({"display_name": dname, "id": pid})
    except Exception as e:
        print(f"  WARNING  ESPN roster failed: {e}")
    return players


def build_nantes_player_map() -> dict[str, dict]:
    """Fetch all Nantes players with their IDs and image paths from fcnantes.com."""
    player_map = {}
    try:
        print("  Fetching FC Nantes roster ...")
        r = requests.get(NANTES_EFFECTIF, headers=NANTES_HEADERS, timeout=15)
        r.raise_for_status()

        # Extract each player block: numjoueur, img_path, prenom, nom
        blocks = re.findall(
            r'fiche\.php\?numjoueur=(\d+).*?<img src="([^"]+)".*?'
            r'<p class="prenom[^>]*>([^<]+)</p>\s*'
            r'<p class="nom[^>]*>([^<]+)</p>',
            r.text,
            re.DOTALL
        )

        for numjoueur, img_path, prenom, nom in blocks:
            full_name = f"{prenom.strip()} {nom.strip()}"
            norm_name = normalize(full_name)
            player_map[norm_name] = {
                "id": numjoueur,
                "img_path": img_path.strip(),
                "full_name": full_name,
            }

        print(f"  Found {len(player_map)} Nantes players")
        return player_map
    except Exception as e:
        print(f"  WARNING  Nantes roster failed: {e}")
        return {}


def get_nantes_image_url(name: str, player_map: dict) -> str | None:
    """Return Nantes official illustration image URL for a player, or None if not found."""
    norm_name = normalize(name)
    if norm_name not in player_map:
        return None

    player = player_map[norm_name]
    # Use the illu200x120 image path directly
    # Path like: /images/joueurs/20252026/illu200x120/carlgren010825.png
    img_path = player["img_path"]
    if img_path:
        return f"https://www.fcnantes.com{img_path}"
    return None


def wp_image_for_player(name: str) -> str | None:
    """Return Wikipedia article thumbnail URL for a player, or None."""
    norm = normalize(name)
    wp_title = WP_OVERRIDES.get(norm, name)

    # Try multiple title variations
    titles_to_try = [wp_title, name]

    for title in titles_to_try:
        try:
            r = requests.get(WP_API, params={
                "action":      "query",
                "titles":      title,
                "prop":        "pageimages",
                "format":      "json",
                "pithumbsize": 500,
            }, headers=WP_HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            pages = r.json().get("query", {}).get("pages", {})
            if pages:
                page = next(iter(pages.values()))
                thumb = page.get("thumbnail", {})
                if thumb and thumb.get("source"):
                    return thumb["source"]
        except Exception as e:
            pass

    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 62)
    print("  FC Nantes — Player Headshot Scraper")
    print("=" * 62)

    espn_roster = build_espn_roster()
    nantes_player_map = build_nantes_player_map()

    # ESPN id map
    espn_id_map: dict[str, str] = {}
    for p in espn_roster:
        espn_id_map[normalize(p["display_name"])] = p["id"]

    print(
        f"\n  ESPN: {len(espn_roster)}  Nantes roster: {len(nantes_player_map)}"
        f"  Target: {len(TARGET_PLAYERS)}"
        f"\n  Output: {OUTPUT_DIR}\n" + "-" * 62
    )

    downloaded, skipped, no_image = 0, 0, []

    for i, name in enumerate(TARGET_PLAYERS, 1):
        filename = safe_filename(name) + ".png"
        filepath = OUTPUT_DIR / filename
        # Use repr() or encode to avoid terminal Unicode issues
        print(f"  [{i:>2}/{len(TARGET_PLAYERS)}] {safe_filename(name).replace('_', ' ').title()}")

        if filepath.exists():
            print(f"           Already exists — skipped")
            skipped += 1
            continue

        # Source 1: FC Nantes official image
        nantes_url = get_nantes_image_url(name, nantes_player_map)
        if nantes_url:
            if download_image(nantes_url, filepath, hdrs=NANTES_HEADERS, min_size=3000):
                kb = filepath.stat().st_size // 1024
                print(f"           [Nantes] -> {filename} ({kb}KB)")
                downloaded += 1
                time.sleep(0.3)
                continue
            else:
                print(f"           Nantes URL found but image unavailable/too small")

        # Source 2: Wikipedia
        wp_url = wp_image_for_player(name)
        if wp_url:
            if download_image(wp_url, filepath, hdrs=HEADERS, min_size=8000):
                kb = filepath.stat().st_size // 1024
                print(f"           [Wikipedia] -> {filename} ({kb}KB)")
                downloaded += 1
                time.sleep(0.2)
                continue
            else:
                print(f"           Wikipedia found but too small")

        # Source 3: ESPN CDN
        espn_id = espn_id_map.get(normalize(name))
        if espn_id:
            espn_url = ESPN_HEADSHOT.format(id=espn_id)
            if download_image(espn_url, filepath, hdrs=HEADERS, min_size=5000):
                kb = filepath.stat().st_size // 1024
                print(f"           [ESPN CDN] -> {filename} ({kb}KB)")
                downloaded += 1
                time.sleep(0.2)
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
