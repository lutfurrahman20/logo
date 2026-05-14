"""
Lille OSC - Player Headshot Downloader (Soccer / Ligue 1)

Sources tried in order per player:
  1. LOSC official roster portraits
  2. Transfermarkt - player profile og:image
  3. Wikipedia - pageimages thumbnail API
  4. ESPN CDN - last resort

Squad source:
  https://www.espn.com/soccer/team/squad/_/id/166/lille
"""

import hashlib
import io
import re
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image


ESPN_ROSTER_API = "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/teams/166/roster"
ESPN_HEADSHOT = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

WP_API = "https://en.wikipedia.org/w/api.php"
TM_SEARCH = "https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche"
TM_PROFILE = "https://www.transfermarkt.com/x/profil/spieler/{id}"
LOSC_ROSTER_PAGES = [
    "https://www.losc.fr/effectif/lille/76",
    "https://www.losc.fr/effectif/lille/78",
]

OUTPUT_DIR = Path("f:/logo/lille_soccer_player_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
WP_HEADERS = {"User-Agent": "logo-collector/1.0 (educational)"}
TM_HEADERS = {**HEADERS, "Referer": "https://www.transfermarkt.com/"}
LOSC_HEADERS = {**HEADERS, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}

OFFICIAL_NAME_ALIASES = {
    "alexsandro victor de souza ribeiro": "alexsandro",
    "andre filipe tavares gomes": "andre gomes",
    "felix alexandre andrade sanches correia": "felix correia",
    "ngal ayel mukau": "ngalayel mukau",
    "tiago carvalho santos": "tiago santos",
}

TARGET_PLAYERS = [
    "Alexsandro Victor de Souza Ribeiro",
    "Andre Filipe Tavares Gomes",
    "Arnaud Bodart",
    "Ayyoub Bouaddi",
    "Aissa Mandi",
    "Benjamin Andre",
    "Berke Ozer",
    "Calvin Verdonk",
    "Chancel Mbemba",
    "Ethan Mbappe",
    "Felix Alexandre Andrade Sanches Correia",
    "Hamza Igamane",
    "Hakon Haraldsson",
    "Marc-Aurele Caillard",
    "Marius Broholm",
    "Matias Fernandez-Pardo",
    "Maxima Goffi",
    "Morgan Costarelli",
    "Nabil Bentaleb",
    "Nathan Ngoy",
    "Ngal'ayel Mukau",
    "Olivier Giroud",
    "Osame Sahraoui",
    "Ousmane Toure",
    "Romain Perraud",
    "Samy Merzouk",
    "Soriba Diaoune",
    "Thomas Meunier",
    "Thomas Sajous",
    "Tiago Carvalho Santos",
    "Ugo Raghouber",
    "Zadig Lanssade",
]

TM_PLAYER_IDS = {
    "alexsandro victor de souza ribeiro": 320263,
    "andre filipe tavares gomes": 221025,
    "andre gomes": 221025,
    "arnaud bodart": 255780,
    "ayyoub bouaddi": 345355,
    "aissa mandi": 117899,
    "benjamin andre": 138649,
    "berke ozer": 257267,
    "calvin verdonk": 283637,
    "chancel mbemba": 183239,
    "ethan mbappe": 355971,
    "felix alexandre andrade sanches correia": 479648,
    "felix correia": 479648,
    "hamza igamane": 288269,
    "hakon haraldsson": 296833,
    "marc aurele caillard": 167905,
    "marius broholm": 310393,
    "matias fernandez pardo": 285948,
    "maxima goffi": 399152,
    "morgan costarelli": 314876,
    "nabil bentaleb": 160272,
    "nathan ngoy": 361159,
    "ngal ayel mukau": 378843,
    "olivier giroud": 9667,
    "osame sahraoui": 391313,
    "ousmane toure": 373405,
    "romain perraud": 247308,
    "samy merzouk": 408649,
    "soriba diaoune": 313549,
    "thomas meunier": 157270,
    "thomas sajous": 341649,
    "tiago carvalho santos": 357547,
    "ugo raghouber": 393301,
    "zadig lanssade": 418093,
}

WP_OVERRIDES = {
    "alexsandro victor de souza ribeiro": "Alexsandro",
    "andre filipe tavares gomes": "Andre Gomes",
    "aissa mandi": "Aissa Mandi",
    "benjamin andre": "Benjamin Andre",
    "berke ozer": "Berke Ozer",
    "ethan mbappe": "Ethan Mbappe",
    "felix alexandre andrade sanches correia": "Felix Correia",
    "hakon haraldsson": "Hakon Haraldsson",
    "marc aurele caillard": "Marc-Aurele Caillard",
    "ngal ayel mukau": "Ngal'ayel Mukau",
    "ousmane toure": "Ousmane Toure",
    "tiago carvalho santos": "Tiago Santos",
}

_CHAR_MAP = str.maketrans(
    {
        "ø": "o",
        "Ø": "O",
        "æ": "ae",
        "Æ": "AE",
        "ß": "ss",
        "ł": "l",
        "Ł": "L",
        "ı": "i",
        "đ": "d",
        "'": " ",
        "\u2019": " ",
    }
)

# Known bad outputs already present in this project:
# - 300x390 repeated silhouette image
# - 172x70 banner-like placeholder image
INVALID_IMAGE_HASHES = {
    "3bc38a53a09035cdf776020f3ec7ea0920f61b591c18c216e7764cab441740c9",
    "f242b9cb420e4d01d95349decd7dbd6b3abdae1802e37c002fd3c541b029cdd0",
}


def normalize(value: str) -> str:
    value = value.translate(_CHAR_MAP)
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[-\s]+", " ", value).strip().lower()


def safe_filename(name: str) -> str:
    normalized = normalize(name)
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    return re.sub(r"[-\s]+", "_", normalized)


def image_sha256(img: Image.Image) -> str:
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def is_invalid_image(img: Image.Image) -> bool:
    width, height = img.size
    digest = image_sha256(img)

    if digest in INVALID_IMAGE_HASHES:
        return True
    if width <= 180 or height <= 120:
        return True
    if width > height:
        return True
    return False


def existing_file_is_valid(filepath: Path) -> bool:
    if not filepath.exists():
        return False

    try:
        img = Image.open(filepath).convert("RGBA")
        return not is_invalid_image(img)
    except Exception:
        return False


def save_image_bytes(content: bytes, filepath: Path) -> bool:
    try:
        img = Image.open(io.BytesIO(content)).convert("RGBA")
        if is_invalid_image(img):
            return False
        filepath.parent.mkdir(parents=True, exist_ok=True)
        img.save(filepath.with_suffix(".png"), "PNG")
        return True
    except Exception as exc:
        print(f"    ERROR    {exc}")
        return False


def download_image(url: str, filepath: Path, hdrs: dict | None = None, min_size: int = 5000) -> bool:
    try:
        response = requests.get(url, headers=hdrs or HEADERS, timeout=20)
        if response.status_code == 200 and len(response.content) >= min_size:
            return save_image_bytes(response.content, filepath)
    except Exception as exc:
        print(f"    ERROR    {exc}")
    return False


def build_espn_roster() -> list[dict]:
    players = []
    try:
        print("  Fetching ESPN roster (team 166 / fra.1) ...")
        response = requests.get(ESPN_ROSTER_API, headers=HEADERS, timeout=20)
        response.raise_for_status()
        for athlete in response.json().get("athletes", []):
            player_id = str(athlete.get("id", ""))
            display_name = athlete.get("displayName", "") or athlete.get("fullName", "")
            if player_id and display_name:
                players.append({"display_name": display_name, "id": player_id})
    except Exception as exc:
        print(f"  WARNING  ESPN roster failed: {exc}")
    return players


def build_losc_player_map() -> dict[str, str]:
    player_map: dict[str, str] = {}

    figure_pattern = re.compile(
        r'<figure class="PlayerSelect-figure.*?</figure>',
        flags=re.DOTALL,
    )
    name_pattern = re.compile(
        r'<span class="PlayerSelect-fullname">\s*([^<]+?)<br><strong>([^<]*)</strong>',
        flags=re.DOTALL,
    )
    hover_pattern = re.compile(
        r'<div class="PlayerSelect-picture-hover">\s*<img[^>]+src="([^"]+)"',
        flags=re.DOTALL,
    )
    still_pattern = re.compile(
        r'<div class="PlayerSelect-picture-initial">.*?<img[^>]+src="([^"]+)"',
        flags=re.DOTALL,
    )

    try:
        for url in LOSC_ROSTER_PAGES:
            print(f"  Fetching LOSC roster page {url} ...")
            response = requests.get(url, headers=LOSC_HEADERS, timeout=20)
            response.raise_for_status()
            html = response.text.replace("&nbsp;", " ")

            for figure in figure_pattern.findall(html):
                name_match = name_pattern.search(figure)
                if not name_match:
                    continue

                first_name = re.sub(r"\s+", " ", name_match.group(1)).strip()
                last_name = re.sub(r"\s+", " ", name_match.group(2)).strip()
                full_name = f"{first_name} {last_name}".strip()

                image_match = hover_pattern.search(figure) or still_pattern.search(figure)
                if not image_match:
                    continue

                image_url = image_match.group(1)
                if image_url.startswith("/"):
                    image_url = f"https://www.losc.fr{image_url}"

                player_map[normalize(full_name)] = image_url

        print(f"  LOSC official players found: {len(player_map)}")
    except Exception as exc:
        print(f"  WARNING  LOSC roster failed: {exc}")

    return player_map


def official_lookup_key(name: str) -> str:
    normalized_name = normalize(name)
    return OFFICIAL_NAME_ALIASES.get(normalized_name, normalized_name)


def tm_profile_image(name: str, tm_id: int | None = None) -> str | None:
    try:
        if tm_id is None:
            response = requests.get(TM_SEARCH, params={"query": name}, headers=TM_HEADERS, timeout=12)
            if response.status_code == 200:
                links = re.findall(r'href="/[^"]+/profil/spieler/(\d+)"', response.text)
                if links:
                    tm_id = int(links[0])

        if tm_id is not None:
            response = requests.get(TM_PROFILE.format(id=tm_id), headers=TM_HEADERS, timeout=15)
            if response.status_code == 200:
                match = re.search(r'og:image[^>]*content="([^"]+)"', response.text)
                if match:
                    return match.group(1)
    except Exception:
        return None
    return None


def wp_image_for_player(name: str) -> str | None:
    normalized_name = normalize(name)
    titles_to_try = [WP_OVERRIDES.get(normalized_name, name), name]

    for title in titles_to_try:
        try:
            response = requests.get(
                WP_API,
                params={
                    "action": "query",
                    "titles": title,
                    "prop": "pageimages",
                    "format": "json",
                    "pithumbsize": 500,
                },
                headers=WP_HEADERS,
                timeout=10,
            )
            if response.status_code != 200:
                continue
            pages = response.json().get("query", {}).get("pages", {})
            if not pages:
                continue
            page = next(iter(pages.values()))
            thumbnail = page.get("thumbnail", {})
            if thumbnail and thumbnail.get("source"):
                return thumbnail["source"]
        except Exception:
            continue

    return None


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 62)
    print("  Lille OSC - Player Headshot Scraper")
    print("=" * 62)

    espn_roster = build_espn_roster()
    losc_player_map = build_losc_player_map()
    espn_id_map = {normalize(player["display_name"]): player["id"] for player in espn_roster}

    print(
        f"\n  ESPN: {len(espn_roster)}  LOSC: {len(losc_player_map)}  Target: {len(TARGET_PLAYERS)}"
        f"\n  Output: {OUTPUT_DIR}\n" + "-" * 62
    )

    downloaded = 0
    skipped = 0
    replaced = 0
    no_image = []

    for index, name in enumerate(TARGET_PLAYERS, 1):
        filename = safe_filename(name) + ".png"
        filepath = OUTPUT_DIR / filename
        normalized_name = normalize(name)
        official_name = official_lookup_key(name)
        losc_url = losc_player_map.get(official_name)
        print(f"  [{index:>2}/{len(TARGET_PLAYERS)}] {name}")

        if losc_url:
            if download_image(losc_url, filepath, hdrs=LOSC_HEADERS, min_size=5000):
                kb = filepath.stat().st_size // 1024
                print(f"           [LOSC] -> {filename} ({kb}KB)")
                downloaded += 1
                time.sleep(0.2)
                continue
            print("           LOSC image found but download failed, falling back")

        if filepath.exists() and existing_file_is_valid(filepath):
            print("           Already exists - valid, skipped")
            skipped += 1
            continue

        if filepath.exists():
            print("           Existing file is invalid placeholder - replacing")
            replaced += 1

        tm_id = TM_PLAYER_IDS.get(normalized_name)
        tm_url = tm_profile_image(name, tm_id)
        if tm_url and download_image(tm_url, filepath, hdrs=TM_HEADERS, min_size=5000):
            kb = filepath.stat().st_size // 1024
            print(f"           [Transfermarkt] -> {filename} ({kb}KB)")
            downloaded += 1
            time.sleep(0.2)
            continue

        wp_url = wp_image_for_player(name)
        if wp_url and download_image(wp_url, filepath, hdrs=HEADERS, min_size=8000):
            kb = filepath.stat().st_size // 1024
            print(f"           [Wikipedia] -> {filename} ({kb}KB)")
            downloaded += 1
            time.sleep(0.2)
            continue

        espn_id = espn_id_map.get(normalized_name)
        if espn_id:
            espn_url = ESPN_HEADSHOT.format(id=espn_id)
            if download_image(espn_url, filepath, hdrs=HEADERS, min_size=5000):
                kb = filepath.stat().st_size // 1024
                print(f"           [ESPN CDN] -> {filename} ({kb}KB)")
                downloaded += 1
                time.sleep(0.2)
                continue

        print("           No image found")
        no_image.append(name)

    print(f"\n{'=' * 62}")
    print(f"  Downloaded : {downloaded}")
    print(f"  Replaced   : {replaced}")
    print(f"  Skipped    : {skipped}")
    print(f"  No image   : {len(no_image)}")
    for name in no_image:
        print(f"    - {name}")
    print(f"  Output     : {OUTPUT_DIR}")
    print(f"{'=' * 62}")


if __name__ == "__main__":
    main()
