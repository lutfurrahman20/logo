import requests
import time
from pathlib import Path

SAVE_DIR = Path(r"f:\logo\laliga_logos")

# save_name -> ESPN displayName
TEAM_MAP = {
    "Athletic Club Bilbao":          "Athletic Club",
    "CA Osasuna":                    "Osasuna",
    "CD Leganés":                    "Leganés",
    "Club Atlético de Madrid":       "Atlético Madrid",
    "Cádiz CF":                      "Cádiz",
    "Deportivo Alavés":              "Alavés",
    "Elche CF":                      "Elche",
    "FC Barcelona":                  "Barcelona",
    "Getafe CF":                     "Getafe",
    "Girona FC":                     "Girona",
    "Granada CF":                    "Granada",
    "Levante UD":                    "Levante",
    "Rayo Vallecano":                "Rayo Vallecano",
    "Real Betis Balompié":           "Real Betis",
    "Real Club Celta de Vigo":       "Celta Vigo",
    "Real Club Deportivo Mallorca":  "Mallorca",
    "Real Madrid CF":                "Real Madrid",
    "Real Oviedo":                   "Real Oviedo",
    "Real Sociedad de Fútbol":       "Real Sociedad",
    "Real Valladolid CF":            "Real Valladolid",
    "Reial Club Deportiu Espanyol":  "Espanyol",
    "Sevilla FC":                    "Sevilla",
    "UD Almería":                    "Almería",
    "UD Las Palmas":                 "Las Palmas",
    "Valencia CF":                   "Valencia",
    "Villarreal CF":                 "Villarreal",
}


def fetch_league_teams(league_slug):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/teams?limit=50"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    teams = data["sports"][0]["leagues"][0]["teams"]
    return {t["team"]["displayName"]: t["team"]["id"] for t in teams}


def download_logo(team_id, save_path):
    url = f"https://a.espncdn.com/i/teamlogos/soccer/500/{team_id}.png"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    save_path.write_bytes(resp.content)


def main():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    # Fetch both divisions to cover relegated/promoted teams
    all_teams = fetch_league_teams("esp.1")
    all_teams.update(fetch_league_teams("esp.2"))

    saved = failed = 0
    for save_name, espn_name in TEAM_MAP.items():
        team_id = all_teams.get(espn_name)
        if team_id is None:
            print(f"NOT FOUND: {save_name!r} (looked for ESPN name {espn_name!r})")
            failed += 1
            continue
        dest = SAVE_DIR / f"{save_name}.png"
        try:
            download_logo(team_id, dest)
            print(f"Saved: {save_name}.png  (id={team_id})")
            saved += 1
        except Exception as e:
            print(f"FAILED: {save_name} — {e}")
            failed += 1
        time.sleep(0.08)

    print(f"\nDone: {saved} saved, {failed} failed")
    print(f"Logos saved to: {SAVE_DIR}")


if __name__ == "__main__":
    main()
