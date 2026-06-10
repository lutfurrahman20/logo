"""
ESPN ICC Women's World Cup Team Logo Downloader
Fetches team logos from ESPN CDN for all tournament teams.
Falls back to TheSportsDB, then Wikipedia when ESPN has no logo.
Source: https://www.espn.com/cricket/standings/series/8584/icc-women's-world-cup
Saves as simple country names (e.g. australia.png, not australia_women.png).
"""

import re
import time
from pathlib import Path

import requests

from cricket_team_logo_fallbacks import HEADERS, download_with_fallbacks

OUTPUT_DIR = Path("f:/logo/icc_womens_world_cup_logos")
API_URL = "https://site.web.api.espn.com/apis/v2/sports/cricket/8584/standings"


def base_country_name(name: str) -> str:
    """Strip women's suffixes so 'Australia Women' becomes 'Australia'."""
    cleaned = re.sub(r"\s+women(?:'s)?\b", "", name, flags=re.I).strip()
    cleaned = re.sub(r"\s+w\b$", "", cleaned, flags=re.I).strip()
    return cleaned or name


def fetch_teams() -> list[dict]:
    """Fetch all unique teams from ESPN standings API."""
    resp = requests.get(API_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    seen: dict[str, dict] = {}
    for child in data.get("children", []):
        for entry in child.get("standings", {}).get("entries", []):
            team = entry["team"]
            team_id = team["id"]
            if team_id in seen:
                continue
            logos = team.get("logos", [])
            if logos:
                display = team["displayName"]
                country = base_country_name(display)
                seen[team_id] = {
                    "name": display,
                    "country": country,
                    "id": team_id,
                    "logo_url": logos[0]["href"],
                }

    return sorted(seen.values(), key=lambda t: t["country"])


def name_to_filename(country: str) -> str:
    """Convert country name to lowercase_underscore filename."""
    return country.lower().replace(" ", "_").replace("-", "_") + ".png"


def wiki_titles_for_country(country: str) -> list[str]:
    return [
        f"{country} women's national cricket team",
        f"{country} women national cricket team",
        f"{country} national cricket team",
        country,
    ]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("ESPN ICC Women's World Cup Logo Downloader")
    print("=" * 60)

    teams = fetch_teams()
    print(f"Found {len(teams)} teams\n")

    ok, fail = 0, 0
    for team in teams:
        filename = name_to_filename(team["country"])
        save_path = OUTPUT_DIR / filename
        print(f"  {team['name']}")
        print(f"    -> {filename}")

        success, source = download_with_fallbacks(
            team["country"],
            team["logo_url"],
            save_path,
            wiki_titles=wiki_titles_for_country(team["country"]),
        )
        if success:
            size = save_path.stat().st_size
            print(f"    [OK] {source} ({size:,} bytes)")
            ok += 1
        else:
            print("    [FAIL] Not found on ESPN, TheSportsDB, or Wikipedia")
            fail += 1
        time.sleep(0.3)

    print(f"\n{'=' * 60}")
    print(f"Done: {ok} downloaded, {fail} failed")
    print(f"Logos saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
