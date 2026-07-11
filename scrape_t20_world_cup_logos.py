"""
ESPN Men's T20 World Cup Team Logo Downloader
Fetches team logos from ESPN CDN for all tournament teams.
Falls back to TheSportsDB, then Wikipedia when ESPN has no logo.
Source: https://www.espn.com/cricket/standings/series/8604/men's-t20-world-cup
Saves as lowercase_underscore filenames.
"""

import time
from pathlib import Path

import requests

from cricket_team_logo_fallbacks import HEADERS, download_with_fallbacks

OUTPUT_DIR = Path("f:/logo/mens_t20_world_cup_logos")
API_URL = "https://site.web.api.espn.com/apis/v2/sports/cricket/8604/standings"


def fetch_teams() -> list[dict]:
    """Fetch all unique teams from ESPN standings API (deduped across groups)."""
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
                seen[team_id] = {
                    "name": team["displayName"],
                    "id": team_id,
                    "logo_url": logos[0]["href"],
                }

    return sorted(seen.values(), key=lambda t: t["name"])


def name_to_filename(name: str) -> str:
    """Convert team display name to lowercase_underscore filename."""
    return name.lower().replace(" ", "_").replace("-", "_") + ".png"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("ESPN Men's T20 World Cup Logo Downloader")
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
