"""
ESPN German Bundesliga Team Logo Downloader
Fetches team logos from ESPN CDN and saves with official team names.
"""

import requests
import time
from pathlib import Path

OUTPUT_DIR = Path("f:/logo/bundesliga_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# All 18 Bundesliga teams — desired save name → ESPN displayName to match
TEAM_MAP = {
    "1. FC Heidenheim 1846":    "1. FC Heidenheim 1846",
    "1. FC Union Berlin":       "1. FC Union Berlin",
    "Bayer Leverkusen":         "Bayer Leverkusen",
    "Bayern Munich":            "Bayern Munich",
    "Borussia Dortmund":        "Borussia Dortmund",
    "Borussia Monchengladbach": "Borussia Mönchengladbach",
    "Eintracht Frankfurt":      "Eintracht Frankfurt",
    "FC Augsburg":              "FC Augsburg",
    "FC Cologne":               "FC Cologne",
    "Hamburg SV":               "Hamburg SV",
    "Mainz":                    "Mainz",
    "RB Leipzig":               "RB Leipzig",
    "SC Freiburg":              "SC Freiburg",
    "St. Pauli":                "St. Pauli",
    "TSG Hoffenheim":           "TSG Hoffenheim",
    "VfB Stuttgart":            "VfB Stuttgart",
    "VfL Wolfsburg":            "VfL Wolfsburg",
    "Werder Bremen":            "Werder Bremen",
}


def fetch_all_teams() -> dict:
    """Fetch all Bundesliga teams from ESPN API, return dict of displayName → team info."""
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/teams?limit=30"
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
    print("  ESPN German Bundesliga Team Logo Downloader")
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
