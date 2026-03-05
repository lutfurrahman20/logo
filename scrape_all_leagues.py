import requests
import json
from pathlib import Path
import time

API_KEY = "3"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# List of all major leagues to scrape
ALL_LEAGUES = [
    # Soccer/Football - Europe
    "English Premier League",
    "Spanish La Liga",
    "German Bundesliga",
    "Italian Serie A",
    "French Ligue 1",
    "Dutch Eredivisie",
    "Portuguese Liga",
    "Scottish Premier League",
    "Belgian Pro League",
    "Turkish Super Lig",
    "Greek Super League",
    "Russian Premier League",
    "Ukrainian Premier League",
    "Austrian Football Bundesliga",
    "Swiss Super League",
    "Danish Superliga",
    "Norwegian Eliteserien",
    "Swedish Allsvenskan",
    
    # Soccer/Football - International & Other
    "UEFA Champions League",
    "English League Championship",
    "English League 1",
    "English League 2",
    "MLS",
    "Brazilian Serie A",
    "Argentine Primera División",
    "Mexican Liga MX",
    "Japanese J League",
    "Chinese Super League",
    "Australian A-League",
    
    # American Sports
    "NFL",
    "NBA",
    "MLB",
    "NHL",
    "NCAAF",
    "NCAAB",
    
    # Other Sports
    "Formula 1",
    "UFC",
    "Australian Football",
    "Rugby League",
    "Rugby Union",
    "Cricket",
]

def download_league_logos(league_name):
    """Download all team logos for a specific league"""
    safe_league_name = league_name.lower().replace(" ", "_").replace("-", "_")
    
    print(f"\n{'='*70}")
    print(f"📥 Fetching: {league_name}")
    print(f"{'='*70}")
    
    url = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}/search_all_teams.php?l={league_name.replace(' ', '%20')}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"❌ Server Error {response.status_code}")
            return 0
        
        data = response.json()
        if not data or not data.get("teams"):
            print(f"⚠️  No teams found")
            return 0
        
        teams = []
        for team_info in data["teams"]:
            team = {
                "name": team_info.get("strTeam"),
                "league": team_info.get("strLeague"),
                "sport": team_info.get("strSport"),
                "logo": team_info.get("strBadge") or team_info.get("strLogo"),
                "stadium": team_info.get("strStadium"),
                "city": team_info.get("strLocation"),
                "country": team_info.get("strCountry"),
            }
            teams.append(team)
        
        print(f"✅ Found {len(teams)} teams")
        
        # Save to JSON
        json_file = f"{safe_league_name}_teams.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(teams, f, indent=2, ensure_ascii=False)
        
        # Download logos
        logos_folder = f"{safe_league_name}_logos"
        Path(logos_folder).mkdir(exist_ok=True)
        
        success = 0
        for i, team in enumerate(teams, 1):
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
                    print(f"  [{i}/{len(teams)}] ✅ {team['name']}")
                    success += 1
                else:
                    print(f"  [{i}/{len(teams)}] ❌ {team['name']} (HTTP {r.status_code})")
            except Exception as e:
                print(f"  [{i}/{len(teams)}] 🛑 {team['name']} ({e})")
        
        print(f"\n✨ Downloaded {success}/{len(teams)} logos → '{logos_folder}/'")
        return success
        
    except Exception as e:
        print(f"🛑 Error: {e}")
        return 0

# Main execution
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🌍 SCRAPING ALL LEAGUES FROM THESPORTSDB")
    print("="*70)
    print(f"\nTotal leagues to scrape: {len(ALL_LEAGUES)}")
    print("This may take a while...\n")
    
    total_teams = 0
    successful_leagues = 0
    
    for i, league in enumerate(ALL_LEAGUES, 1):
        print(f"\n[{i}/{len(ALL_LEAGUES)}] Starting: {league}")
        
        teams_downloaded = download_league_logos(league)
        
        if teams_downloaded > 0:
            total_teams += teams_downloaded
            successful_leagues += 1
        
        # Be polite to the API - add a small delay between requests
        if i < len(ALL_LEAGUES):
            time.sleep(2)
    
    print("\n" + "="*70)
    print("🎉 SCRAPING COMPLETE!")
    print("="*70)
    print(f"✅ Successful leagues: {successful_leagues}/{len(ALL_LEAGUES)}")
    print(f"✅ Total team logos downloaded: {total_teams}")
    print("\nAll logos saved to their respective folders!")
    print("="*70 + "\n")
