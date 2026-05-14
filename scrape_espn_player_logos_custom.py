"""
Soccer Player Logo Scraper - With Custom Name Mapping

Downloads player headshots using EXACT names you provide.
Filenames will be exactly your names converted to lowercase with underscores.

Usage:
    python scrape_espn_player_logos_custom.py "URL" "custom_names.txt"
    
Where custom_names.txt contains one player name per line (full names as you want them).
"""

import hashlib
import io
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image


# ESPN API endpoints
ESPN_ROSTER_API = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{team_id}/roster"

# Alternative image sources
TM_SEARCH = "https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche"
TM_PROFILE = "https://www.transfermarkt.com/{player}/profil/spieler/{id}"
WP_API = "https://en.wikipedia.org/w/api.php"

# Bundesliga official body photos (face + jersey)
BUNDESLIGA_SQUAD_URL = "https://www.bundesliga.com/en/bundesliga/clubs/{slug}/squad"
BUNDESLIGA_BODY_IMG = "https://assets.bundesliga.com/player/{dfl_id}-body.png"

# ESPN team slug -> WordPress joueurs API base URL (for clubs with WP sites)
ESPN_TO_WP_API = {
    "strasbourg":           "https://www.rcstrasbourgalsace.fr/wp-json/wp/v2/joueurs",
    "rc-strasbourg":        "https://www.rcstrasbourgalsace.fr/wp-json/wp/v2/joueurs",
    "rc-strasbourg-alsace": "https://www.rcstrasbourgalsace.fr/wp-json/wp/v2/joueurs",
}

# ESPN team slug -> Drupal squad page URL (for clubs using Drupal CMS)
# Images scraped from /equipe-pro with small_player_card style -> upgraded to hero_player
ESPN_TO_DRUPAL_SQUAD = {
    "stade-rennais": "https://www.staderennais.com/equipe-pro",
    "rennes":        "https://www.staderennais.com/equipe-pro",
}

# ESPN team name -> Bundesliga slug mapping
ESPN_TO_BUNDESLIGA_SLUG = {
    "bayern-munich":            "fc-bayern-muenchen",
    "bayer-leverkusen":         "bayer-04-leverkusen",
    "borussia-dortmund":        "borussia-dortmund",
    "borussia-monchengladbach": "borussia-moenchengladbach",
    "eintracht-frankfurt":      "eintracht-frankfurt",
    "rb-leipzig":               "rb-leipzig",
    "sc-freiburg":              "sport-club-freiburg",
    "vfb-stuttgart":            "vfb-stuttgart",
    "wolfsburg":                "vfl-wolfsburg",
    "vfl-wolfsburg":            "vfl-wolfsburg",
    "hoffenheim":               "tsg-1899-hoffenheim",
    "tsg-hoffenheim":           "tsg-1899-hoffenheim",
    "werder-bremen":            "sv-werder-bremen",
    "fc-augsburg":              "fc-augsburg",
    "augsburg":                 "fc-augsburg",
    "fc-cologne":               "1-fc-koeln",
    "hamburg-sv":               "hamburger-sv",
    "union-berlin":             "1-fc-union-berlin",
    "fc-union-berlin":          "1-fc-union-berlin",
    "mainz":                    "1-fsv-mainz-05",
    "heidenheim":               "1-fc-heidenheim-1846",
    "1-fc-heidenheim":          "1-fc-heidenheim-1846",
    "bochum":                   "vfl-bochum-1848",
    "fc-st-pauli":              "fc-st-pauli",
    "st-pauli":                 "fc-st-pauli",
    "holstein-kiel":            "holstein-kiel",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
TM_HEADERS = {**HEADERS, "Referer": "https://www.transfermarkt.com/"}
WP_HEADERS = {"User-Agent": "logo-collector/1.0 (educational)"}

# Aliases for player names that differ between data sources and Transfermarkt
TM_NAME_ALIASES: dict[str, str] = {
    # Rennes
    "nordan mukiele": "Nordi Mukiele",
    "mousa mohammad mousa sulaiman al ta'mari": "Mousa Tamari",
    "mousa al-tamari": "Mousa Tamari",
}

# Known invalid image hashes (placeholders/silhouettes)
INVALID_IMAGE_HASHES = {
    "3bc38a53a09035cdf776020f3ec7ea0920f61b591c18c216e7764cab441740c9",
    "f242b9cb420e4d01d95349decd7dbd6b3abdae1802e37c002fd3c541b029cdd0",
}

# Character normalization map
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


def normalize(value: str) -> str:
    """Normalize text for comparison."""
    value = value.translate(_CHAR_MAP)
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[-\s]+", " ", value).strip().lower()


def safe_filename(name: str) -> str:
    """Convert player name to safe filename (lowercase with underscores)."""
    # Replace spaces with underscores, convert to lowercase
    filename = name.lower()
    # Remove accents and special characters
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")
    # Replace spaces and hyphens with underscores
    filename = re.sub(r"[-\s]+", "_", filename)
    # Remove any remaining non-alphanumeric characters (except underscores)
    filename = re.sub(r"[^\w_]", "", filename)
    return filename


def image_sha256(img: Image.Image) -> str:
    """Calculate SHA256 hash of image."""
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def is_invalid_image(img: Image.Image) -> bool:
    """Check if image is a placeholder or invalid."""
    width, height = img.size
    digest = image_sha256(img)

    if digest in INVALID_IMAGE_HASHES:
        return True
    if width <= 180 or height <= 120:
        return True
    if width > height:  # Landscape images are usually placeholders
        return True
    return False


def save_image_bytes(content: bytes, filepath: Path) -> bool:
    """Save image bytes to file after validation."""
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


def download_image(url: str, filepath: Path, hdrs: dict | None = None, min_size: int = 3000) -> bool:
    """Download image from URL and save to filepath."""
    try:
        response = requests.get(url, headers=hdrs or HEADERS, timeout=20)
        if response.status_code == 200 and len(response.content) >= min_size:
            return save_image_bytes(response.content, filepath)
    except Exception as exc:
        print(f"    ERROR    {exc}")
    return False


def name_to_bundesliga_slug(name: str) -> str:
    """Convert player full name to Bundesliga URL slug (lowercase, hyphens)."""
    slug = unicodedata.normalize("NFKD", name)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug.strip())
    return slug


def build_bundesliga_player_map(team_slug: str) -> dict[str, str]:
    """
    Scrape the Bundesliga squad page and return a mapping of
    player-slug -> DFL body image URL.
    """
    url = BUNDESLIGA_SQUAD_URL.format(slug=team_slug)
    player_map: dict[str, str] = {}
    try:
        print(f"  Fetching Bundesliga squad page: {url}")
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        # Extract ordered player slugs and ordered DFL IDs
        slugs = re.findall(r'href="/en/bundesliga/player/([a-z0-9\-]+)"', r.text)
        dfl_ids = re.findall(
            r'assets\.bundesliga\.com/player/(dfl-obj-[a-z0-9]+-dfl-clu-[a-z0-9]+-dfl-sea-[a-z0-9]+)-circle\.png',
            r.text
        )
        for slug, dfl_id in zip(slugs, dfl_ids):
            body_url = BUNDESLIGA_BODY_IMG.format(dfl_id=dfl_id)
            player_map[slug] = body_url
        print(f"  Found {len(player_map)} players with official body photos")
    except Exception as exc:
        print(f"  WARNING  Bundesliga squad page failed: {exc}")
    return player_map


def bundesliga_body_image(name: str, player_map: dict[str, str]) -> str | None:
    """Look up official Bundesliga body image URL for a player by name."""
    slug = name_to_bundesliga_slug(name)
    # Try exact slug match
    if slug in player_map:
        return player_map[slug]
    # Try partial match (first two words of name)
    words = slug.split("-")
    if len(words) >= 2:
        partial = f"{words[0]}-{words[1]}"
        for map_slug, url in player_map.items():
            if map_slug.startswith(partial) or partial in map_slug:
                return url
    # Try last name only
    if words:
        last = words[-1]
        for map_slug, url in player_map.items():
            if map_slug.endswith(last) or map_slug.startswith(last):
                return url
    return None


def tm_profile_image(name: str) -> str | None:
    """Get player image from Transfermarkt."""
    # Apply name alias if available
    search_name = TM_NAME_ALIASES.get(name.lower(), name)
    try:
        # Search for player on Transfermarkt
        response = requests.get(
            TM_SEARCH, 
            params={"query": search_name}, 
            headers=TM_HEADERS, 
            timeout=12
        )
        if response.status_code == 200:
            # Find player profile link
            links = re.findall(r'href="(/[^"]+/profil/spieler/(\d+))"', response.text)
            if links:
                profile_path, player_id = links[0]
                # Get profile page
                profile_url = f"https://www.transfermarkt.com{profile_path}"
                response = requests.get(profile_url, headers=TM_HEADERS, timeout=15)
                if response.status_code == 200:
                    # Extract og:image
                    match = re.search(r'og:image[^>]*content="([^"]+)"', response.text)
                    if match:
                        return match.group(1)
    except Exception:
        return None
    return None


def wp_image_for_player(name: str) -> str | None:
    """Get player image from Wikipedia."""
    try:
        response = requests.get(
            WP_API,
            params={
                "action": "query",
                "titles": name,
                "prop": "pageimages",
                "format": "json",
                "pithumbsize": 500,
            },
            headers=WP_HEADERS,
            timeout=10,
        )
        if response.status_code != 200:
            return None
            
        pages = response.json().get("query", {}).get("pages", {})
        if not pages:
            return None
            
        page = next(iter(pages.values()))
        thumbnail = page.get("thumbnail", {})
        if thumbnail and thumbnail.get("source"):
            return thumbnail["source"]
    except Exception:
        return None
    return None


def parse_espn_url(url: str) -> tuple[str, str, str]:
    """
    Parse ESPN team squad URL to extract team_id, league, and team name.
    
    Example: https://www.espn.com/soccer/team/squad/_/id/132/bayern-munich
    Returns: ("132", "ger.1", "bayern-munich")
    """
    # Extract team ID
    match = re.search(r'/id/(\d+)', url)
    if not match:
        raise ValueError(f"Could not extract team ID from URL: {url}")
    team_id = match.group(1)
    
    # Extract team name (last part of URL)
    parts = url.rstrip('/').split('/')
    team_name = parts[-1] if parts else "unknown"
    
    # Try to detect league from URL or use a common mapping
    league = detect_league(url, team_id)
    
    return team_id, league, team_name


def detect_league(url: str, team_id: str) -> str:
    """
    Detect league slug from URL or team ID.
    Common leagues: eng.1 (EPL), ger.1 (Bundesliga), esp.1 (La Liga), 
                     ita.1 (Serie A), fra.1 (Ligue 1), uefa.champions (UCL)
    """
    # Common team ID to league mapping (add more as needed)
    TEAM_LEAGUE_MAP = {
        # Bundesliga (ger.1)
        "132": "ger.1",  # Bayern Munich
        "131": "ger.1",  # Bayer Leverkusen
        "133": "ger.1",  # Borussia Dortmund
        # EPL (eng.1)
        "364": "eng.1",  # Manchester United
        "359": "eng.1",  # Liverpool
        "363": "eng.1",  # Manchester City
        "362": "eng.1",  # Chelsea
        "361": "eng.1",  # Arsenal
        # La Liga (esp.1)
        "83": "esp.1",   # Barcelona
        "86": "esp.1",   # Real Madrid
        "95": "esp.1",   # Atletico Madrid
        # Serie A (ita.1)
        "108": "ita.1",  # Juventus
        "103": "ita.1",  # AC Milan
        "110": "ita.1",  # Inter Milan
        # Ligue 1 (fra.1)
        "160": "fra.1",  # PSG
        "166": "fra.1",  # Lille
        "167": "fra.1",  # Lyon
        "169": "fra.1",  # Marseille
        "2502": "fra.1", # OGC Nice
        "180": "fra.1",  # RC Strasbourg
    }
    
    if team_id in TEAM_LEAGUE_MAP:
        return TEAM_LEAGUE_MAP[team_id]
    
    # Default fallback
    return "ger.1"


def build_wp_player_map(api_url: str) -> dict[str, str]:
    """
    Fetch WordPress joueurs custom post type and return {slug: image_url} mapping.
    Uses batch media fetch instead of _embed for speed.
    """
    # Step 1: collect all player slugs + featured_media IDs (fast, no _embed)
    slug_to_media: dict[str, int] = {}
    page = 1
    while True:
        try:
            r = requests.get(api_url, params={"per_page": 100, "page": page}, headers=HEADERS, timeout=30)
            if r.status_code not in (200,) or not r.content:
                break
            players = r.json()
            if not players:
                break
            for p in players:
                slug = p.get("slug", "")
                media_id = p.get("featured_media", 0)
                if slug and media_id:
                    slug_to_media[slug] = media_id
            if len(players) < 100:
                break
            page += 1
        except Exception as exc:
            print(f"  WARNING  WP API page {page} failed: {exc}")
            break

    if not slug_to_media:
        print("  Found 0 players with official photos (WP API)")
        return {}

    # Step 2: batch-fetch media items to get source URLs
    base_url = api_url.replace("/joueurs", "").replace("/wp-json/wp/v2", "") + "/wp-json/wp/v2/media"
    # Parse base domain from api_url
    base_match = re.match(r"(https://[a-zA-Z0-9._-]+)", api_url)
    if base_match:
        base_url = base_match.group(1) + "/wp-json/wp/v2/media"

    media_id_to_url: dict[int, str] = {}
    all_ids = list(set(slug_to_media.values()))
    # Batch in chunks of 50
    for i in range(0, len(all_ids), 50):
        chunk = all_ids[i:i + 50]
        try:
            r2 = requests.get(
                base_url,
                params={"include": ",".join(str(m) for m in chunk), "per_page": 100},
                headers=HEADERS,
                timeout=30,
            )
            if r2.status_code == 200:
                for m in r2.json():
                    url = m.get("source_url", "")
                    if url:
                        media_id_to_url[m["id"]] = url
        except Exception as exc:
            print(f"  WARNING  WP media batch failed: {exc}")

    # Step 3: build final slug -> image_url map
    player_map: dict[str, str] = {}
    for slug, media_id in slug_to_media.items():
        url = media_id_to_url.get(media_id, "")
        if url:
            player_map[slug] = url

    print(f"  Found {len(player_map)} players with official photos (WP API)")
    return player_map


def wp_club_jersey_image(name: str, player_map: dict[str, str]) -> str | None:
    """Fuzzy-match a player name to a WordPress slug and return image URL."""
    # Normalize name to slug form
    def to_slug(s: str) -> str:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s = re.sub(r"[^a-z0-9\s-]", "", s.lower())
        return re.sub(r"[\s]+", "-", s.strip())

    name_slug = to_slug(name)
    name_words = set(name_slug.split("-"))

    # 1. Exact slug match
    if name_slug in player_map:
        return player_map[name_slug]

    # 2. Any slug that starts with first-word + second-word
    name_parts = name_slug.split("-")
    if len(name_parts) >= 2:
        prefix2 = f"{name_parts[0]}-{name_parts[1]}"
        for slug, url in player_map.items():
            if slug.startswith(prefix2) or f"-{prefix2}-" in f"-{slug}-":
                return url

    # 3. All name words appear in the slug (handles reordered names)
    significant = [w for w in name_words if len(w) > 2 and w not in ("da", "de", "di", "van", "von", "le", "la", "el", "do", "du")]
    if significant:
        for slug, url in player_map.items():
            slug_words = set(slug.split("-"))
            # If all significant name words are in the slug
            if all(any(nw in sw or sw in nw for sw in slug_words) for nw in significant):
                return url

    # 3b. At least 2 significant words match (handles long names like "Ogbonna Stanley Chizurum" -> slug "stanley-ogbonna")
    if len(significant) >= 2:
        for slug, url in player_map.items():
            slug_words = set(slug.split("-"))
            matched = sum(1 for nw in significant if any(nw in sw or sw in nw for sw in slug_words))
            if matched >= 2:
                return url

    # 4. Last-name fallback
    if name_parts:
        last = name_parts[-1]
        if len(last) > 3:
            for slug, url in player_map.items():
                if slug.endswith(f"-{last}") or slug.startswith(f"{last}-") or slug == last:
                    return url

    # 5. First-name fallback  
    if name_parts:
        first = name_parts[0]
        if len(first) > 3:
            for slug, url in player_map.items():
                if slug.startswith(f"{first}-"):
                    return url

    return None


def build_drupal_player_map(squad_url: str) -> dict[str, str]:
    """
    Scrape a Drupal-based club squad page (e.g. staderennais.com/equipe-pro).
    Returns {player-slug: hero_image_url} by pairing ordered slugs with ordered card images.
    """
    player_map: dict[str, str] = {}
    base = re.match(r"(https://[a-zA-Z0-9._-]+)", squad_url)
    base_url = base.group(1) if base else ""
    try:
        r = requests.get(squad_url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        text = r.text
        # Extract ordered card image paths (small_player_card style)
        card_paths = re.findall(
            r"/sites/default/files/styles/small_player_card/private/[^\s\"\'<>?]+\.webp",
            text,
        )
        # Extract ordered player slugs from /equipe-pro/{slug} links
        slugs = re.findall(r"/equipe-pro/([a-z][a-z0-9-]+)(?=\")", text)
        # Deduplicate preserving order
        seen_paths, seen_slugs = [], []
        for p in card_paths:
            if p not in seen_paths:
                seen_paths.append(p)
        for s in slugs:
            if s not in seen_slugs:
                seen_slugs.append(s)
        # Pair them 1:1 and upgrade to hero_player style
        for slug, card_path in zip(seen_slugs, seen_paths):
            hero_path = card_path.replace("/small_player_card/", "/hero_player/")
            player_map[slug] = base_url + hero_path
        print(f"  Found {len(player_map)} players with official photos (Drupal squad page)")
    except Exception as exc:
        print(f"  WARNING  Drupal squad page failed: {exc}")
    return player_map


# Reuse wp_club_jersey_image fuzzy matching for Drupal maps too
drupal_jersey_image = wp_club_jersey_image


def load_custom_names(filepath: Path) -> list[str]:
    """Load custom player names from file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        names = [line.strip() for line in f if line.strip()]
    return names


def download_player_logos_custom(custom_names: list[str], team_name: str, output_dir: Path = None) -> None:
    """Download all player logos using custom exact names."""
    if output_dir is None:
        output_dir = Path(f"f:/logo/{team_name.replace('-', '_')}_player_logos")
    
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build Bundesliga body-photo map if this is a Bundesliga team
    bundesliga_slug = ESPN_TO_BUNDESLIGA_SLUG.get(team_name)
    bundesliga_map: dict[str, str] = {}
    if bundesliga_slug:
        bundesliga_map = build_bundesliga_player_map(bundesliga_slug)

    # Build WordPress club API map if this team has a WP site (e.g. Strasbourg)
    wp_api_url = ESPN_TO_WP_API.get(team_name)
    wp_map: dict[str, str] = {}
    if wp_api_url:
        wp_map = build_wp_player_map(wp_api_url)

    # Build Drupal squad page map if applicable (e.g. Rennes)
    drupal_squad_url = ESPN_TO_DRUPAL_SQUAD.get(team_name)
    drupal_map: dict[str, str] = {}
    if drupal_squad_url:
        drupal_map = build_drupal_player_map(drupal_squad_url)

    if bundesliga_map:
        sources = "Bundesliga (jersey), Transfermarkt, Wikipedia"
    elif wp_map:
        sources = "Club website (jersey), Transfermarkt, Wikipedia"
    elif drupal_map:
        sources = "Club website (jersey), Transfermarkt, Wikipedia"
    else:
        sources = "Transfermarkt, Wikipedia"
    
    print("=" * 70)
    print(f"  Soccer Player Logo Scraper (Custom Names)")
    print(f"  Team: {team_name.replace('-', ' ').title()}")
    print(f"  Sources: {sources}")
    print(f"  Output: {output_dir}")
    print("=" * 70)
    
    print(f"\n  Starting downloads for {len(custom_names)} players...")
    print("-" * 70)
    
    downloaded = 0
    failed = 0
    no_image = []
    
    for index, full_name in enumerate(custom_names, 1):
        # Generate filename from EXACT user-provided name
        filename = safe_filename(full_name) + ".png"
        filepath = output_dir / filename
        
        print(f"  [{index:>2}/{len(custom_names)}] {full_name}")

        # 1. Try Bundesliga official body photo (face + jersey) first
        if bundesliga_map:
            bl_url = bundesliga_body_image(full_name, bundesliga_map)
            if bl_url and download_image(bl_url, filepath, hdrs=HEADERS, min_size=10000):
                kb = filepath.stat().st_size // 1024
                print(f"           [Bundesliga] -> {filename} ({kb}KB)")
                downloaded += 1
                time.sleep(0.2)
                continue

        # 1b. Try WordPress club website jersey photo
        if wp_map:
            wp_url = wp_club_jersey_image(full_name, wp_map)
            if wp_url and download_image(wp_url, filepath, hdrs=HEADERS, min_size=5000):
                kb = filepath.stat().st_size // 1024
                print(f"           [Club website] -> {filename} ({kb}KB)")
                downloaded += 1
                time.sleep(0.3)
                continue

        # 1c. Try Drupal club website jersey photo (e.g. Rennes)
        if drupal_map:
            d_url = drupal_jersey_image(full_name, drupal_map)
            if d_url and download_image(d_url, filepath, hdrs=HEADERS, min_size=5000):
                kb = filepath.stat().st_size // 1024
                print(f"           [Club website] -> {filename} ({kb}KB)")
                downloaded += 1
                time.sleep(0.3)
                continue
        
        # 2. Fallback: Transfermarkt (face only)
        tm_url = tm_profile_image(full_name)
        if tm_url and download_image(tm_url, filepath, hdrs=TM_HEADERS, min_size=5000):
            kb = filepath.stat().st_size // 1024
            print(f"           [Transfermarkt] -> {filename} ({kb}KB)")
            downloaded += 1
            time.sleep(0.5)
            continue
        
        # 3. Last resort: Wikipedia
        wp_url = wp_image_for_player(full_name)
        if wp_url and download_image(wp_url, filepath, hdrs=HEADERS, min_size=8000):
            kb = filepath.stat().st_size // 1024
            print(f"           [Wikipedia] -> {filename} ({kb}KB)")
            downloaded += 1
            time.sleep(0.3)
            continue
        
        print(f"           No image found")
        no_image.append(full_name)
        failed += 1
    
    print(f"\n{'=' * 70}")
    print(f"  Downloaded : {downloaded}")
    print(f"  No image   : {len(no_image)}")
    if no_image and len(no_image) <= 10:
        for name in no_image:
            print(f"    - {name}")
    print(f"  Output     : {output_dir}")
    print(f"{'=' * 70}")


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python scrape_espn_player_logos_custom.py <ESPN_URL> <custom_names_file>")
        print()
        print("Example:")
        print("  python scrape_espn_player_logos_custom.py \\")
        print("    'https://www.espn.com/soccer/team/squad/_/id/132/bayern-munich' \\")
        print("    'bayern_players.txt'")
        print()
        print("The custom_names_file should contain one player name per line.")
        print("Filenames will be exactly your names in lowercase with underscores.")
        sys.exit(1)
    
    url = sys.argv[1]
    names_file = Path(sys.argv[2])
    
    if not names_file.exists():
        print(f"ERROR: File not found: {names_file}")
        sys.exit(1)
    
    try:
        team_id, league, team_name = parse_espn_url(url)
        custom_names = load_custom_names(names_file)
        print(f"Loaded {len(custom_names)} custom player names from {names_file}")
        download_player_logos_custom(custom_names, team_name)
    except Exception as exc:
        print(f"\nERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
