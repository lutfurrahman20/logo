"""
ESPN Serie A Team Logo Downloader
Fetches team logos from ESPN CDN and saves with official team names.
"""

import requests
from pathlib import Path

SAVE_DIR = Path(r"f:\logo\seriea_logos")

# save name -> ESPN team ID
TEAMS = {
    "AC Milan":                 103,
    "AC Monza":                 4007,
    "ACF Fiorentina":           109,
    "AS Roma":                  104,
    "Atalanta Bergamasca Calcio": 105,
    "Bologna FC 1909":          107,
    "Cagliari Calcio":          2925,
    "Calcio Como 1907":         2572,
    "Empoli FC":                2574,
    "FC Internazionale Milano": 110,
    "Frosinone Calcio":         4057,
    "Genoa CFC":                3263,
    "Hellas Verona FC":         119,
    "Juventus FC":              111,
    "Parma Calcio 1913":        115,
    "Pisa Sporting Club":       3956,
    "SS Lazio":                 112,
    "SSC Napoli":               114,
    "Torino FC":                239,
    "US Cremonese":             4050,
    "US Lecce":                 113,
    "US Salernitana 1919":      3240,
    "US Sassuolo Calcio":       3997,
    "Udinese Calcio":           118,
    "Venezia FC":               17530,
}


def main():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    saved, failed = 0, 0

    for name, team_id in sorted(TEAMS.items()):
        url = f"https://a.espncdn.com/i/teamlogos/soccer/500/{team_id}.png"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            save_path = SAVE_DIR / f"{name}.png"
            save_path.write_bytes(resp.content)
            print(f"Saved:  {name}  (id={team_id})")
            saved += 1
        except Exception as e:
            print(f"FAILED: {name}  (id={team_id}) — {e}")
            failed += 1

    print(f"\nDone: {saved} saved, {failed} failed")
    print(f"Logos saved to: {SAVE_DIR}")


if __name__ == "__main__":
    main()
