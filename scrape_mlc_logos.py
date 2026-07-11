"""
Major League Cricket (MLC) Team Logo Downloader
Fetches team logos from the official MLC CMS used by majorleaguecricket.com.
Falls back to TheSportsDB, then Wikipedia when a logo URL is missing.
Source: https://www.majorleaguecricket.com/teams
Saves as lowercase_underscore filenames.
"""

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

OUTPUT_DIR = Path("f:/logo/mlc_logos")
SITE_URL = "https://www.majorleaguecricket.com/teams"
BLOB_BASE = "https://splcms.blob.core.windows.net/cricketnest/client_1/mlc_match_center"
LEAGUE_NAME = "Major League Cricket"


def discover_teamlist_url() -> str:
    """Find the current TeamList JSON path from the MLC site bundle."""
    page = requests.get(SITE_URL, headers=HEADERS, timeout=30)
    page.raise_for_status()
    match = re.search(r"main\.[a-f0-9]+\.js", page.text)
    if not match:
        return f"{BLOB_BASE}/TeamList/1210-TeamList.json"

    js_url = f"https://www.majorleaguecricket.com/{match.group(0)}"
    js = requests.get(js_url, headers=HEADERS, timeout=30).text
    refs = re.findall(r"TeamList/\d+-TeamList\.json", js)
    if refs:
        return f"{BLOB_BASE}/{refs[0]}"
    return f"{BLOB_BASE}/TeamList/1210-TeamList.json"


def fetch_teams() -> list[dict]:
    """Fetch MLC teams from the official CMS team list."""
    teamlist_url = discover_teamlist_url()
    resp = requests.get(teamlist_url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    teams = []
    for entry in data.get("CompetitionTeams", []):
        display = (entry.get("DisplayName") or entry.get("TeamName") or "").strip()
        if not display:
            continue
        name = display.title()
        logo_url = entry.get("TeamProfile") or entry.get("TeamImage") or ""
        teams.append({
            "name": name,
            "id": str(entry.get("TeamID", "")),
            "logo_url": logo_url,
            "backup_url": entry.get("TeamImage") or "",
        })

    return sorted(teams, key=lambda t: t["name"])


def name_to_filename(name: str) -> str:
    """Convert team display name to lowercase_underscore filename."""
    return name.lower().replace(" ", "_").replace("-", "_") + ".png"


def download_mlc_logo(team: dict, save_path: Path) -> tuple[bool, str]:
    """Try official MLC logo URLs, then shared fallbacks."""
    for label, url in [
        ("MLC", team.get("logo_url")),
        ("MLC alt", team.get("backup_url")),
    ]:
        if url and download_logo(url, save_path):
            return True, label

    print("    MLC failed - trying TheSportsDB...")
    tsdb_url = fetch_from_thesportsdb(team["name"], league=LEAGUE_NAME)
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
    print("Major League Cricket Logo Downloader")
    print("=" * 60)

    teams = fetch_teams()
    print(f"Found {len(teams)} teams\n")

    ok, fail = 0, 0
    for team in teams:
        filename = name_to_filename(team["name"])
        save_path = OUTPUT_DIR / filename
        print(f"  {team['name']}")
        print(f"    -> {filename}")

        success, source = download_mlc_logo(team, save_path)
        if success:
            size = save_path.stat().st_size
            print(f"    [OK] {source} ({size:,} bytes)")
            ok += 1
        else:
            print("    [FAIL] Not found on MLC, TheSportsDB, or Wikipedia")
            fail += 1
        time.sleep(0.3)

    print(f"\n{'=' * 60}")
    print(f"Done: {ok} downloaded, {fail} failed")
    print(f"Logos saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
