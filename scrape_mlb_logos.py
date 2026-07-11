"""
ESPN MLB Team Logo Downloader
Fetches team logos from ESPN CDN and saves with official team names.
"""

import requests
import time
from pathlib import Path

OUTPUT_DIR = Path("f:/logo/mlb_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# All 30 MLB teams — desired save name → ESPN displayName to match
# (key = filename without .png, value = ESPN displayName to look up)
TEAM_MAP = {
    "Arizona Diamondbacks":  "Arizona Diamondbacks",
    "Athletics":             "Athletics",
    "Atlanta Braves":        "Atlanta Braves",
    "Baltimore Orioles":     "Baltimore Orioles",
    "Boston Red Sox":        "Boston Red Sox",
    "Chicago Cubs":          "Chicago Cubs",
    "Chicago White Sox":     "Chicago White Sox",
    "Cincinnati Reds":       "Cincinnati Reds",
    "Cleveland Guardians":   "Cleveland Guardians",
    "Colorado Rockies":      "Colorado Rockies",
    "Detroit Tigers":        "Detroit Tigers",
    "Houston Astros":        "Houston Astros",
    "Kansas City Royals":    "Kansas City Royals",
    "Los Angeles Angels":    "Los Angeles Angels",
    "Los Angeles Dodgers":   "Los Angeles Dodgers",
    "Miami Marlins":         "Miami Marlins",
    "Milwaukee Brewers":     "Milwaukee Brewers",
    "Minnesota Twins":       "Minnesota Twins",
    "New York Mets":         "New York Mets",
    "New York Yankees":      "New York Yankees",
    "Philadelphia Phillies": "Philadelphia Phillies",
    "Pittsburgh Pirates":    "Pittsburgh Pirates",
    "San Diego Padres":      "San Diego Padres",
    "San Francisco Giants":  "San Francisco Giants",
    "Seattle Mariners":      "Seattle Mariners",
    "St. Louis Cardinals":   "St. Louis Cardinals",
    "Tampa Bay Rays":        "Tampa Bay Rays",
    "Texas Rangers":         "Texas Rangers",
    "Toronto Blue Jays":     "Toronto Blue Jays",
    "Washington Nationals":  "Washington Nationals",
}


def fetch_all_teams() -> dict:
    """Fetch all MLB teams from ESPN API, return dict of displayName → team info."""
    url = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/teams?limit=50"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    raw_teams = (
        data
        .get("sports", [{}])[0]
        .get("leagues", [{}])[0]
        .get("teams", [])
    )

    teams = {}
    for item in raw_teams:
        team = item.get("team", item)
        tid = str(team.get("id", ""))
        dn = team.get("displayName", "")
        if tid and dn:
            teams[dn] = {
                "id":               tid,
                "displayName":      dn,
                "shortDisplayName": team.get("shortDisplayName", ""),
                "abbreviation":     team.get("abbreviation", "").lower(),
            }
    return teams


def download_logo(team_id: str, save_path: Path) -> bool:
    """Download a team logo PNG from ESPN CDN."""
    url = f"https://a.espncdn.com/i/teamlogos/mlb/500/{team_id}.png"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 500:
            save_path.write_bytes(r.content)
            return True
        print(f"    WARNING HTTP {r.status_code} or empty response for {url}")
    except Exception as exc:
        print(f"    ERROR {exc}")
    return False


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("  ESPN MLB Team Logo Downloader")
    print("=" * 65)
    print("  Fetching team list from ESPN API ...")

    all_teams = fetch_all_teams()
    print(f"  Found {len(all_teams)} teams in ESPN API\n")

    success, failed = 0, []

    for save_name, espn_name in TEAM_MAP.items():
        team_info = all_teams.get(espn_name)

        if team_info is None:
            # Fallback: case-insensitive search
            espn_lower = espn_name.lower()
            for dn, info in all_teams.items():
                if dn.lower() == espn_lower:
                    team_info = info
                    break

        if team_info is None:
            print(f"  MISS   {save_name!r}  — no ESPN match found")
            failed.append(save_name)
            continue

        save_path = OUTPUT_DIR / f"{save_name}.png"
        ok = download_logo(team_info["id"], save_path)
        if ok:
            print(
                f"  OK     {save_name!r:<30} "
                f"← {team_info['displayName']}  (id={team_info['id']})"
            )
            success += 1
        else:
            print(f"  FAIL   {save_name!r}")
            failed.append(save_name)

        time.sleep(0.08)

    print()
    print("=" * 65)
    print(f"  Done: {success} saved, {len(failed)} failed")
    if failed:
        print("  Failed teams:")
        for name in failed:
            print(f"    - {name}")
    print(f"  Logos saved to: {OUTPUT_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()
