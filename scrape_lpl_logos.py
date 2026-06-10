"""
Lanka Premier League (LPL) Team Logo Downloader
Fetches team logos from ESPNcricinfo image CDN for all LPL teams.
Falls back to TheSportsDB, then Wikipedia when a logo is missing.
Source: https://www.espncricinfo.com/series/lanka-premier-league-2024-1421415/teams
Saves as lowercase_underscore filenames.
"""

import json
import re
import time
from pathlib import Path

import requests

from cricket_team_logo_fallbacks import (
    HEADERS,
    download_logo,
    fetch_from_thesportsdb,
    fetch_from_wikipedia,
)

CRICINFO_HEADERS = {
    **HEADERS,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.espncricinfo.com/",
}

OUTPUT_DIR = Path("f:/logo/lpl_logos")
SERIES_URL = "https://www.espncricinfo.com/series/lanka-premier-league-2024-1421415/teams"
SERIES_ID = "1421415"
ESPN_API_URL = f"https://site.web.api.espn.com/apis/v2/sports/cricket/{SERIES_ID}/standings"
CRICINFO_IMG_BASE = "https://img1.hscicdn.com/image/upload"
LEAGUE_NAME = "Lanka Premier League"

SLUG_TO_NAME = {
    "colombo-kaps": "Colombo Kaps",
    "dambulla-sixers": "Dambulla Thunders",
    "galle-gallants": "Galle Gallants",
    "jaffna-kings": "Jaffna Kings",
    "kandy-royals": "Kandy Royals",
}

# Known ESPNcricinfo logo paths for LPL 2024 teams page.
SLUG_TO_IMAGE = {
    "colombo-kaps": "/lsci/db/PICTURES/CMS/417700/417703.png",
    "dambulla-sixers": "/lsci/db/PICTURES/CMS/417700/417704.png",
    "galle-gallants": "/lsci/db/PICTURES/CMS/417700/417705.png",
    "jaffna-kings": "/lsci/db/PICTURES/CMS/417700/417706.png",
    "kandy-royals": "/lsci/db/PICTURES/CMS/417700/417707.png",
}

TSDB_ALIASES = {
    "Dambulla Thunders": ["Dambulla Sixers"],
    "Colombo Kaps": ["Colombo Strikers"],
    "Kandy Royals": ["B-Love Kandy", "Kandy Falcons"],
    "Galle Gallants": ["Galle Marvels", "Galle Titans"],
}


def cricinfo_logo_url(image_path: str) -> str:
    """Build a full ESPNcricinfo CDN URL from a /lsci/... image path."""
    path = image_path.lstrip("/")
    return f"{CRICINFO_IMG_BASE}/{path}"


def fetch_teams_from_espn() -> dict[str, str]:
    """Return ESPN display names keyed by normalized team name."""
    resp = requests.get(ESPN_API_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    names: dict[str, str] = {}
    for child in data.get("children", []):
        for entry in child.get("standings", {}).get("entries", []):
            display = entry["team"]["displayName"]
            names[display.lower()] = display
    return names


def parse_teams_from_next_data(data: dict, espn_names: dict[str, str]) -> dict[str, dict]:
    """Extract LPL team logos from ESPNcricinfo __NEXT_DATA__."""
    found: dict[str, dict] = {}

    def walk(obj):
        if isinstance(obj, dict):
            slug = obj.get("slug", "")
            image_url = obj.get("imageUrl")
            if slug in SLUG_TO_NAME and image_url:
                default_name = SLUG_TO_NAME[slug]
                name = espn_names.get(default_name.lower(), default_name)
                if slug not in found or obj.get("image"):
                    found[slug] = {
                        "name": name,
                        "slug": slug,
                        "logo_url": cricinfo_logo_url(image_url),
                    }
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)

    walk(data)
    return found


def fetch_teams_from_cricinfo() -> list[dict]:
    """Parse team logos from the ESPNcricinfo teams page."""
    espn_names = fetch_teams_from_espn()
    found: dict[str, dict] = {}

    try:
        resp = requests.get(SERIES_URL, headers=CRICINFO_HEADERS, timeout=30)
        resp.raise_for_status()
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, re.S)
        if match:
            found = parse_teams_from_next_data(json.loads(match.group(1)), espn_names)
    except Exception:
        pass

    if not found:
        for slug, image_path in SLUG_TO_IMAGE.items():
            default_name = SLUG_TO_NAME[slug]
            found[slug] = {
                "name": espn_names.get(default_name.lower(), default_name),
                "slug": slug,
                "logo_url": cricinfo_logo_url(image_path),
            }

    return sorted(found.values(), key=lambda t: t["name"])


def name_to_filename(name: str) -> str:
    """Convert team display name to lowercase_underscore filename."""
    return name.lower().replace(" ", "_").replace("-", "_") + ".png"


def download_lpl_logo(team: dict, save_path: Path) -> tuple[bool, str]:
    """Try ESPNcricinfo CDN first, then shared fallbacks."""
    if team.get("logo_url") and download_logo(team["logo_url"], save_path):
        return True, "ESPNcricinfo"

    print("    ESPNcricinfo failed - trying TheSportsDB...")
    tsdb_url = fetch_from_thesportsdb(
        team["name"],
        league=LEAGUE_NAME,
        aliases=TSDB_ALIASES.get(team["name"]),
    )
    if tsdb_url and download_logo(tsdb_url, save_path):
        return True, "TheSportsDB"

    print("    TheSportsDB failed - trying Wikipedia...")
    wiki_url = fetch_from_wikipedia(team["name"], title_aliases=[team["name"]])
    if wiki_url and download_logo(wiki_url, save_path):
        return True, "Wikipedia"

    return False, ""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("Lanka Premier League Logo Downloader")
    print("=" * 60)

    teams = fetch_teams_from_cricinfo()
    print(f"Found {len(teams)} teams\n")

    ok, fail = 0, 0
    for team in teams:
        filename = name_to_filename(team["name"])
        save_path = OUTPUT_DIR / filename
        print(f"  {team['name']}")
        print(f"    -> {filename}")

        success, source = download_lpl_logo(team, save_path)
        if success:
            size = save_path.stat().st_size
            print(f"    [OK] {source} ({size:,} bytes)")
            ok += 1
        else:
            print("    [FAIL] Not found on ESPNcricinfo, TheSportsDB, or Wikipedia")
            fail += 1
        time.sleep(0.3)

    print(f"\n{'=' * 60}")
    print(f"Done: {ok} downloaded, {fail} failed")
    print(f"Logos saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
