"""
ESPN English Premier League Team Logo Downloader
Fetches team logos from ESPN CDN and saves with official team names.
"""

import requests
import time
from pathlib import Path

OUTPUT_DIR = Path("f:/logo/epl_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# All 20 EPL teams — desired save name → ESPN displayName to match
TEAM_MAP = {
    "AFC Bournemouth":          "AFC Bournemouth",
    "Arsenal":                  "Arsenal",
    "Aston Villa":              "Aston Villa",
    "Brentford":                "Brentford",
    "Brighton & Hove Albion":   "Brighton & Hove Albion",
    "Burnley":                  "Burnley",
    "Chelsea":                  "Chelsea",
    "Crystal Palace":           "Crystal Palace",
    "Everton":                  "Everton",
    "Fulham":                   "Fulham",
    "Leeds United":             "Leeds United",
    "Liverpool":                "Liverpool",
    "Manchester City":          "Manchester City",
    "Manchester United":        "Manchester United",
    "Newcastle United":         "Newcastle United",
    "Nottingham Forest":        "Nottingham Forest",
    "Sunderland":               "Sunderland",
    "Tottenham Hotspur":        "Tottenham Hotspur",
    "West Ham United":          "West Ham United",
    "Wolverhampton Wanderers":  "Wolverhampton Wanderers",
}


def fetch_all_teams() -> dict:
    """Fetch all EPL teams from ESPN API, return dict of displayName → team info."""
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams?limit=30"
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
    """Download logo from ESPN CDN. Returns True on success."""
    url = f"https://a.espncdn.com/i/teamlogos/soccer/500/{team_id}.png"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200 and len(resp.content) > 500:
            save_path.write_bytes(resp.content)
            return True
        return False
    except requests.RequestException:
        return False


def main():
    print()
    print("=" * 65)
    print("  ESPN English Premier League Team Logo Downloader")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("  Fetching team list from ESPN API ...")
    all_teams = fetch_all_teams()
    print(f"  Found {len(all_teams)} teams in ESPN API")
    print()

    saved = 0
    failed = []

    for save_name, espn_name in TEAM_MAP.items():
        team = all_teams.get(espn_name)
        if not team:
            print(f"  MISS   '{save_name}'  (not found in ESPN API as '{espn_name}')")
            failed.append(save_name)
            continue

        save_path = OUTPUT_DIR / f"{save_name}.png"
        ok = download_logo(team["id"], save_path)

        if ok:
            label = f"'{save_name}'"
            espn_label = f"{espn_name}  (id={team['id']})"
            print(f"  OK     {label:<38} ← {espn_label}")
            saved += 1
        else:
            print(f"  FAIL   '{save_name}'  (id={team['id']})")
            failed.append(save_name)

        time.sleep(0.08)

    print()
    print("=" * 65)
    print(f"  Done: {saved} saved, {len(failed)} failed")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    print(f"  Logos saved to: {OUTPUT_DIR}")
    print("=" * 65)
    print()


if __name__ == "__main__":
    main()
