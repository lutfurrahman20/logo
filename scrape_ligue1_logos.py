"""
ESPN French Ligue 1 Team Logo Downloader
Fetches team logos from ESPN CDN and saves with official team names.
Teams not in current Ligue 1 are fetched from the Ligue 2 API.
"""

import requests
import time
from pathlib import Path

OUTPUT_DIR = Path("f:/logo/ligue1_logos")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

# Desired save name → ESPN displayName to match in API
# Teams currently in Ligue 2 (relegated/promoted) are still found via fra.2 API
TEAM_MAP = {
    "AS Monaco FC":                      "AS Monaco",
    "AS Saint-Étienne":                  "Saint-Étienne",
    "Angers Sporting Club de l'Ouest":   "Angers",
    "Association Jeunesse Auxerroise":   "AJ Auxerre",
    "Clermont Foot 63":                  "Clermont Foot",
    "En Avant Guingamp":                 "Guingamp",
    "FC Lorient":                        "Lorient",
    "FC Metz":                           "Metz",
    "FC Nantes":                         "Nantes",
    "Le Havre AC":                       "Le Havre AC",
    "Lille OSC":                         "Lille",
    "Montpellier HSC":                   "Montpellier",
    "OGC Nice Côte d'Azur":             "Nice",
    "Olympique Lyonnais":                "Lyon",
    "Olympique de Marseille":            "Marseille",
    "Paris FC":                          "Paris FC",
    "Paris Saint-Germain FC":            "Paris Saint-Germain",
    "RC Strasbourg Alsace":              "Strasbourg",
    "Racing Club de Lens":               "Lens",
    "Stade Brestois 29":                 "Brest",
    "Stade Rennais FC":                  "Stade Rennais",
    "Stade de Reims":                    "Stade de Reims",
    "Toulouse FC":                       "Toulouse",
    "US du Littoral de Dunkerque":       "Dunkerque",
}

# Teams not in any French ESPN league API — None = skip entirely
SKIP = {
    "Brentford FC",   # English Premier League team, not a French club
}


def fetch_league_teams(league_slug: str) -> dict:
    """Fetch all teams for a given ESPN soccer league slug."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/teams?limit=30"
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
    print("  ESPN French Ligue 1 Team Logo Downloader")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch from both Ligue 1 and Ligue 2 (covers relegated/promoted teams)
    print("  Fetching team list from ESPN API (Ligue 1 + Ligue 2) ...")
    all_teams = {}
    all_teams.update(fetch_league_teams("fra.1"))
    all_teams.update(fetch_league_teams("fra.2"))
    print(f"  Found {len(all_teams)} teams total across both leagues")
    print()

    saved = 0
    failed = []
    skipped = []

    # Process all 25 requested teams
    all_requested = list(TEAM_MAP.keys()) + list(SKIP)
    for save_name in list(TEAM_MAP.keys()) + sorted(SKIP):
        if save_name in SKIP:
            print(f"  SKIP   '{save_name}'  (not a French club)")
            skipped.append(save_name)
            continue

        espn_name = TEAM_MAP[save_name]
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
            print(f"  OK     {label:<44} ← {espn_label}")
            saved += 1
        else:
            print(f"  FAIL   '{save_name}'  (id={team['id']})")
            failed.append(save_name)

        time.sleep(0.08)

    print()
    print("=" * 65)
    print(f"  Done: {saved} saved, {len(failed)} failed, {len(skipped)} skipped")
    if failed:
        print(f"  Failed: {', '.join(failed)}")
    if skipped:
        print(f"  Skipped: {', '.join(skipped)}")
    print(f"  Logos saved to: {OUTPUT_DIR}")
    print("=" * 65)
    print()


if __name__ == "__main__":
    main()
