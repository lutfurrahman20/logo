"""
Toulouse FC - Player Headshot Downloader (Soccer / Ligue 1)

Sources tried in order per player:
  1. Toulouse FC official player page image (from sitemap + player page metadata)
  2. Transfermarkt - player profile og:image
  3. Wikipedia - pageimages thumbnail API
  4. ESPN CDN - last resort

Squad source:
  https://www.espn.com/soccer/team/squad/_/id/179/toulouse
"""

import difflib
import hashlib
import io
import re
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image


ESPN_ROSTER_API = "https://site.api.espn.com/apis/site/v2/sports/soccer/fra.1/teams/179/roster"
ESPN_HEADSHOT = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"

WP_API = "https://en.wikipedia.org/w/api.php"
TM_SEARCH = "https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche"
TM_PROFILE = "https://www.transfermarkt.com/x/profil/spieler/{id}"

TOULOUSE_SITEMAP_URL = "https://www.toulousefc.com/sitemap.xml"
TOULOUSE_PLAYER_BASE = "https://www.toulousefc.com/equipes/equipe-professionnelle/{slug}"

OUTPUT_DIR = Path("f:/logo/toulouse_soccer_player_logos")

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
TFC_HEADERS = {**HEADERS, "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}

TARGET_PLAYERS = [
    "Abu Francis",
    "Alexis Vossah",
    "Aron Donnum",
    "Charlie Cresswell",
    "Cristian Casseres",
    "Darris Zema",
    "Dayann Methalie",
    "Djibril Sidibe",
    "Emersonn Correia da Silva",
    "Enzo Faty",
    "Frank Magri",
    "Frederic Efuele Ngoyala",
    "Gaetan Bakhouche",
    "Guillaume Restes",
    "Ilyas Azizi",
    "Julian Vignolo",
    "Kjetil Haug",
    "Mark McKenzie",
    "Mario Sauer",
    "Naime Said Mchindra",
    "Nicolas Wasbauer",
    "Niklas Schmidt",
    "Noah Edjouma",
    "Noah Lahmadi",
    "Rafik Messali",
    "Rasmus Nicolaisen",
    "Santiago Hidalgo",
    "Seny Koumbassa",
    "Thibaud-Dorian Garondo",
    "Warren Kamanzi",
    "Yann Gboho",
    "Alex Dominguez",
]

OFFICIAL_SLUG_OVERRIDES = {
    "cristian casseres": "cristian-casseres-jr",
    "darris zema": "darris-tema",
    "emersonn correia da silva": "emersonn-correia",
    "frederic efuele ngoyala": "frederic-efuele",
    "gaetan bakhouche": "gaetan-backouche",
    "alex dominguez": "alex-dominguez",
}

WP_OVERRIDES = {
    "aron donnum": "Aron Donnum",
    "cristian casseres": "Cristian Casseres Jr.",
    "djibril sidibe": "Djibril Sidibe",
    "mario sauer": "Mario Sauer",
    "alex dominguez": "Alex Dominguez",
}

INVALID_IMAGE_HASHES = {
    "3bc38a53a09035cdf776020f3ec7ea0920f61b591c18c216e7764cab441740c9",
    "f242b9cb420e4d01d95349decd7dbd6b3abdae1802e37c002fd3c541b029cdd0",
}

CHAR_MAP = str.maketrans(
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


def normalize(value: str) -> str:
    value = value.translate(CHAR_MAP)
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[-\s]+", " ", value).strip().lower()


def to_slug(name: str) -> str:
    base = normalize(name)
    base = re.sub(r"[^\w\s-]", "", base)
    return re.sub(r"[-\s]+", "-", base).strip("-")


def safe_filename(name: str) -> str:
    base = normalize(name)
    base = re.sub(r"[^\w\s-]", "", base)
    return re.sub(r"[-\s]+", "_", base)


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
        print("  Fetching ESPN roster (team 179 / fra.1) ...")
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


def build_toulouse_slug_set() -> set[str]:
    try:
        print("  Fetching Toulouse FC sitemap ...")
        response = requests.get(TOULOUSE_SITEMAP_URL, headers=TFC_HEADERS, timeout=30)
        response.raise_for_status()
        slugs = set(
            slug
            for slug in re.findall(
                r"<loc>https://www\.toulousefc\.com/equipes/equipe-professionnelle/([^<]+)</loc>",
                response.text,
            )
            if "/" not in slug
        )
        print(f"  Toulouse official player slugs: {len(slugs)}")
        return slugs
    except Exception as exc:
        print(f"  WARNING  Toulouse sitemap failed: {exc}")
        return set()


def slug_for_player(name: str, slug_set: set[str]) -> str | None:
    normalized_name = normalize(name)
    if normalized_name in OFFICIAL_SLUG_OVERRIDES:
        custom = OFFICIAL_SLUG_OVERRIDES[normalized_name]
        if custom in slug_set:
            return custom

    candidate = to_slug(name)
    if candidate in slug_set:
        return candidate

    words = [w for w in normalized_name.split() if len(w) >= 3]
    if words:
        scored = []
        for slug in slug_set:
            parts = slug.split("-")
            score = sum(1 for w in words if w in parts)
            if score >= 2 or (len(words) == 1 and words[0] in parts):
                scored.append((score, slug))
        if scored:
            scored.sort(key=lambda item: (-item[0], item[1]))
            return scored[0][1]

    close = difflib.get_close_matches(candidate, list(slug_set), n=1, cutoff=0.72)
    if close:
        return close[0]
    return None


def toulouse_official_image(slug: str) -> str | None:
    url = TOULOUSE_PLAYER_BASE.format(slug=slug)
    try:
        response = requests.get(url, headers=TFC_HEADERS, timeout=20)
        if response.status_code != 200:
            return None

        meta_tags = re.findall(r"<meta[^>]+>", response.text, flags=re.IGNORECASE)
        for tag in meta_tags:
            low = tag.lower()
            if "og:image" not in low and "twitter:image" not in low:
                continue
            match = re.search(
                r"content\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s>]+))",
                tag,
                flags=re.IGNORECASE,
            )
            if not match:
                continue
            image_url = match.group(1) or match.group(2) or match.group(3)
            if not image_url:
                continue
            if image_url.startswith("//"):
                image_url = f"https:{image_url}"
            elif image_url.startswith("/"):
                image_url = f"https://www.toulousefc.com{image_url}"

            if "/media/" in image_url:
                return image_url
    except Exception as exc:
        print(f"    Toulouse page error for {slug}: {exc}")
    return None


def tm_profile_image(name: str) -> str | None:
    try:
        search = requests.get(TM_SEARCH, params={"query": name}, headers=TM_HEADERS, timeout=12)
        if search.status_code != 200:
            return None
        links = re.findall(r'href="/[^"]+/profil/spieler/(\d+)"', search.text)
        if not links:
            return None
        tm_id = int(links[0])

        profile = requests.get(TM_PROFILE.format(id=tm_id), headers=TM_HEADERS, timeout=15)
        if profile.status_code != 200:
            return None
        match = re.search(r'og:image[^>]*content="([^"]+)"', profile.text)
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
            thumb = page.get("thumbnail", {})
            if thumb and thumb.get("source"):
                return thumb["source"]
        except Exception:
            continue
    return None


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 62)
    print("  Toulouse FC - Player Headshot Scraper")
    print("=" * 62)

    espn_roster = build_espn_roster()
    slug_set = build_toulouse_slug_set()
    espn_id_map = {normalize(player["display_name"]): player["id"] for player in espn_roster}

    print(
        f"\n  ESPN: {len(espn_roster)}  Toulouse slugs: {len(slug_set)}  Target: {len(TARGET_PLAYERS)}"
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
        print(f"  [{index:>2}/{len(TARGET_PLAYERS)}] {name}")

        slug = slug_for_player(name, slug_set)
        if slug:
            official_url = toulouse_official_image(slug)
            if official_url and download_image(official_url, filepath, hdrs=TFC_HEADERS, min_size=5000):
                kb = filepath.stat().st_size // 1024
                print(f"           [Toulouse] {slug} -> {filename} ({kb}KB)")
                downloaded += 1
                time.sleep(0.2)
                continue

        if filepath.exists() and existing_file_is_valid(filepath):
            print("           Already exists - valid, skipped")
            skipped += 1
            continue

        if filepath.exists():
            print("           Existing file is invalid placeholder - replacing")
            replaced += 1
            try:
                filepath.unlink()
            except OSError:
                pass

        tm_url = tm_profile_image(name)
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
