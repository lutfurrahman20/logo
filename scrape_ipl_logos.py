"""
ESPN Indian Premier League (Cricket) Team Logo Downloader
Fetches team logos from ESPN CDN for all IPL teams.
Falls back to TheSportsDB, then Wikipedia when ESPN has no logo.
Source: https://www.espn.com/cricket/standings/series/8048/ipl
Saves as lowercase_underscore filenames.
"""

import time
from pathlib import Path

import requests

from cricket_team_logo_fallbacks import HEADERS, download_with_fallbacks

OUTPUT_DIR = Path("f:/logo/ipl_logos")
API_URL = "https://site.web.api.espn.com/apis/v2/sports/cricket/8048/standings"
LEAGUE_NAME = "Indian Premier League"


def fetch_teams() -> list[dict]:
    """Fetch IPL teams from ESPN standings API."""
    resp = requests.get(API_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    entries = data["children"][0]["standings"]["entries"]
    teams = []
    for entry in entries:
        team = entry["team"]
        logos = team.get("logos", [])
        if logos:
            teams.append({
                "name": team["displayName"],
                "id": team["id"],
                "logo_url": logos[0]["href"],
            })
    return teams


def name_to_filename(name: str) -> str:
    """Convert team display name to lowercase_underscore filename."""
    return name.lower().replace(" ", "_").replace("-", "_") + ".png"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("ESPN Indian Premier League Logo Downloader")
    print("=" * 60)

    teams = fetch_teams()
    print(f"Found {len(teams)} teams\n")

    ok, fail = 0, 0
    for team in teams:
        filename = name_to_filename(team["name"])
        save_path = OUTPUT_DIR / filename
        print(f"  {team['name']}")
        print(f"    -> {filename}")
        success, source = download_with_fallbacks(
            team["name"],
            team["logo_url"],
            save_path,
            league=LEAGUE_NAME,
            wiki_titles=[team["name"]],
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
