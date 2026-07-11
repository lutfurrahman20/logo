"""
Soccer Player Logo Scraper - Generic for any ESPN team

Downloads player headshots for any soccer team from ESPN squad page.
NOTE: ESPN doesn't host soccer player images, so this scraper uses alternative sources:
  1. Transfermarkt - player profile og:image  
  2. Wikipedia - pageimages thumbnail API
  
Usage:
    python scrape_espn_player_logos.py "https://www.espn.com/soccer/team/squad/_/id/132/bayern-munich"
    
Player images are saved as lowercase with underscores.
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
    normalized = normalize(name)
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    return re.sub(r"[-\s]+", "_", normalized)


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


def tm_profile_image(name: str) -> str | None:
    """Get player image from Transfermarkt."""
    try:
        # Search for player on Transfermarkt
        response = requests.get(
            TM_SEARCH, 
            params={"query": name}, 
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
    # For now, we'll try common leagues and fall back to detection
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
    }
    
    if team_id in TEAM_LEAGUE_MAP:
        return TEAM_LEAGUE_MAP[team_id]
    
    # Default fallback - try common leagues in order
    return "ger.1"  # Default to Bundesliga for the given example


def fetch_espn_roster(team_id: str, league: str) -> list[dict]:
    """Fetch team roster from ESPN API."""
    api_url = ESPN_ROSTER_API.format(league=league, team_id=team_id)
    players = []
    
    try:
        print(f"  Fetching ESPN roster ...")
        print(f"  API: {api_url}")
        response = requests.get(api_url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        for athlete in data.get("athletes", []):
            display_name = athlete.get("displayName", "") or athlete.get("fullName", "")
            position_data = athlete.get("position", {})
            position = position_data.get("abbreviation", "N/A") if isinstance(position_data, dict) else "N/A"
            
            if display_name:
                players.append({
                    "display_name": display_name,
                    "position": position
                })
        
        print(f"  Found {len(players)} players")
    except Exception as exc:
        print(f"  ERROR: ESPN roster fetch failed: {exc}")
        raise
    
    return players


def download_player_logos(team_id: str, league: str, team_name: str, output_dir: Path = None) -> None:
    """Download all player logos for a team using alternative sources."""
    if output_dir is None:
        output_dir = Path(f"f:/logo/{team_name.replace('-', '_')}_player_logos")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print(f"  Soccer Player Logo Scraper")
    print(f"  Team: {team_name.replace('-', ' ').title()}")
    print(f"  Sources: Transfermarkt, Wikipedia")
    print(f"  Output: {output_dir}")
    print("=" * 70)
    
    # Fetch roster from ESPN
    players = fetch_espn_roster(team_id, league)
    
    if not players:
        print("\n  No players found. Check if team ID and league are correct.")
        return
    
    print(f"\n  Starting downloads for {len(players)} players...")
    print("-" * 70)
    
    downloaded = 0
    failed = 0
    no_image = []
    
    for index, player in enumerate(players, 1):
        name = player["display_name"]
        position = player.get("position", "N/A")
        
        # Generate filename (lowercase with underscores)
        filename = safe_filename(name) + ".png"
        filepath = output_dir / filename
        
        print(f"  [{index:>2}/{len(players)}] {name} ({position})")
        
        # Try Transfermarkt first
        tm_url = tm_profile_image(name)
        if tm_url and download_image(tm_url, filepath, hdrs=TM_HEADERS, min_size=5000):
            kb = filepath.stat().st_size // 1024
            print(f"           [Transfermarkt] -> {filename} ({kb}KB)")
            downloaded += 1
            time.sleep(0.5)  # Be nice to Transfermarkt
            continue
        
        # Try Wikipedia
        wp_url = wp_image_for_player(name)
        if wp_url and download_image(wp_url, filepath, hdrs=HEADERS, min_size=8000):
            kb = filepath.stat().st_size // 1024
            print(f"           [Wikipedia] -> {filename} ({kb}KB)")
            downloaded += 1
            time.sleep(0.3)
            continue
        
        print(f"           No image found")
        no_image.append(name)
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
    if len(sys.argv) < 2:
        print("Usage: python scrape_espn_player_logos.py <ESPN_TEAM_SQUAD_URL>")
        print()
        print("Example:")
        print("  python scrape_espn_player_logos.py 'https://www.espn.com/soccer/team/squad/_/id/132/bayern-munich'")
        print()
        print("Note: ESPN doesn't host soccer player images, so this script uses")
        print("      Transfermarkt and Wikipedia as alternative sources.")
        sys.exit(1)
    
    url = sys.argv[1]
    
    try:
        team_id, league, team_name = parse_espn_url(url)
        download_player_logos(team_id, league, team_name)
    except Exception as exc:
        print(f"\nERROR: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
