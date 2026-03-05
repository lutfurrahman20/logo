import requests
import json
from pathlib import Path

API_KEY = "3"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def get_league_teams(league_name):
    """Fetch teams for a specific league"""
    url = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}/search_all_teams.php?l={league_name.replace(' ', '%20')}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and data.get("teams"):
                return data["teams"]
    except:
        pass
    return None

def download_league_logos(league_name):
    """Download all team logos for a league"""
    print(f"\nFetching {league_name} teams...\n")
    
    teams_data = get_league_teams(league_name)
    
    if not teams_data:
        print(f"❌ No teams found for '{league_name}'")
        return
    
    teams = []
    for team_info in teams_data:
        team = {
            "name": team_info.get("strTeam"),
            "league": team_info.get("strLeague"),
            "logo": team_info.get("strBadge") or team_info.get("strLogo"),
            "stadium": team_info.get("strStadium"),
            "city": team_info.get("strLocation"),
        }
        teams.append(team)
        print(f"✅ {team['name']}")
    
    # Save to JSON
    safe_league_name = league_name.lower().replace(" ", "_")
    json_file = f"{safe_league_name}_teams.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(teams, f, indent=2, ensure_ascii=False)
    
    print(f"\n✨ Found {len(teams)} teams!")
    print(f"📄 Saved to '{json_file}'")
    
    # Download logos
    logos_folder = f"{safe_league_name}_logos"
    Path(logos_folder).mkdir(exist_ok=True)
    
    print(f"\nDownloading logos...\n")
    success = 0
    for team in teams:
        logo_url = team.get("logo")
        if not logo_url:
            continue
        
        safe_name = team["name"].replace(" ", "_").replace("/", "_").replace(".", "")
        extension = logo_url.split(".")[-1].split("?")[0]
        filename = f"{safe_name}.{extension}"
        filepath = f"{logos_folder}/{filename}"
        
        try:
            r = requests.get(logo_url, timeout=10)
            if r.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(r.content)
                print(f"✅ {team['name']} → {filename}")
                success += 1
        except:
            pass
    
    print(f"\n✨ Downloaded {success}/{len(teams)} logos to '{logos_folder}/' folder\n")

# Popular leagues available in TheSportsDB
POPULAR_LEAGUES = {
    "Soccer/Football": [
        "English Premier League",
        "Spanish La Liga", 
        "German Bundesliga",
        "Italian Serie A",
        "French Ligue 1",
        "UEFA Champions League",
        "Dutch Eredivisie",
        "Portuguese Liga",
    ],
    "American Sports": [
        "NFL",
        "NBA",
        "MLB",
        "NHL",
        "MLS",
    ],
    "Other Sports": [
        "Australian Football",
        "Rugby League",
        "Cricket",
        "Motorsport",
    ]
}

print("=" * 60)
print("THESPORTSDB - LEAGUE LOGO DOWNLOADER")
print("=" * 60)
print("\nPopular Leagues Available:\n")

for category, leagues in POPULAR_LEAGUES.items():
    print(f"\n{category}:")
    for league in leagues:
        print(f"  • {league}")

print("\n" + "=" * 60)
print("\nUSAGE:")
print("  1. Edit this script and uncomment a league below")
print("  2. Or add: download_league_logos('Your League Name')")
print("=" * 60)

# Uncomment any of these to download:
# download_league_logos("Italian Serie A")
# download_league_logos("NHL")
# download_league_logos("UEFA Champions League")
# download_league_logos("Dutch Eredivisie")
# download_league_logos("Portuguese Liga")
# download_league_logos("MLS")

print("\n💡 TIP: Already downloaded leagues:")
print("  ✅ English Premier League")
print("  ✅ Spanish La Liga")
print("  ✅ German Bundesliga")
print("  ✅ French Ligue 1")
print("  ✅ NFL")
print("  ✅ NBA")
print("  ✅ MLB")
