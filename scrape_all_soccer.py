import requests
import json
from pathlib import Path
import time

API_KEY = "3"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Comprehensive list of all soccer leagues worldwide
SOCCER_LEAGUES = [
    # England
    "English Premier League",
    "English League Championship",
    "English League 1",
    "English League 2",
    "English National League",
    "English FA Cup",
    "English League Cup",
    
    # Spain
    "Spanish La Liga",
    "Spanish La Liga 2",
    "Spanish Copa del Rey",
    
    # Germany
    "German Bundesliga",
    "German 2. Bundesliga",
    "German DFB Pokal",
    
    # Italy
    "Italian Serie A",
    "Italian Serie B",
    "Italian Coppa Italia",
    
    # France
    "French Ligue 1",
    "French Ligue 2",
    "French Coupe de France",
    
    # Netherlands
    "Dutch Eredivisie",
    "Dutch Eerste Divisie",
    
    # Portugal
    "Portuguese Liga",
    "Portuguese Segunda Liga",
    
    # Scotland
    "Scottish Premier League",
    "Scottish Championship",
    
    # Other European
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
    "Polish Ekstraklasa",
    "Czech First League",
    "Romanian Liga I",
    "Croatian First League",
    "Serbian SuperLiga",
    
    # UEFA Competitions
    "UEFA Champions League",
    "UEFA Europa League",
    "UEFA Conference League",
    
    # Americas
    "MLS",
    "USL Championship",
    "Mexican Liga MX",
    "Argentine Primera División",
    "Brazilian Serie A",
    "Brazilian Serie B",
    "Chilean Primera División",
    "Colombian Primera A",
    "Ecuadorian Serie A",
    "Peruvian Primera División",
    "Uruguayan Primera División",
    "Venezuelan Primera División",
    
    # Asia
    "Japanese J League",
    "Japanese J2 League",
    "Chinese Super League",
    "Korean K League 1",
    "Indian Super League",
    "Saudi Pro League",
    "Qatar Stars League",
    "UAE Pro League",
    "Thai Premier League",
    "Malaysian Super League",
    "Indonesian Liga 1",
    "Vietnamese V.League 1",
    
    # Africa
    "South African Premier League",
    "Egyptian Premier League",
    "Nigerian Professional League",
    "Moroccan Botola",
    "Algerian Ligue 1",
    "Tunisian Ligue 1",
    
    # Oceania
    "Australian A-League",
    "New Zealand Football Championship",
]

def download_league_logos(league_name):
    """Download all team logos for a specific league"""
    safe_league_name = league_name.lower().replace(" ", "_").replace(".", "").replace("-", "_")
    
    print(f"\n{'='*70}")
    print(f"⚽ {league_name}")
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
                "logo": team_info.get("strBadge") or team_info.get("strLogo"),
                "stadium": team_info.get("strStadium"),
                "city": team_info.get("strLocation"),
                "country": team_info.get("strCountry"),
            }
            teams.append(team)
        
        print(f"✅ Found {len(teams)} teams")
        
        # Save to JSON
        json_folder = "soccer_data"
        Path(json_folder).mkdir(exist_ok=True)
        json_file = f"{json_folder}/{safe_league_name}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(teams, f, indent=2, ensure_ascii=False)
        
        # Download logos
        logos_folder = f"soccer_logos/{safe_league_name}"
        Path(logos_folder).mkdir(parents=True, exist_ok=True)
        
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
                    print(f"  [{i:2d}/{len(teams)}] ✅ {team['name']}")
                    success += 1
            except:
                pass
        
        print(f"💾 {success}/{len(teams)} logos saved")
        return success
        
    except Exception as e:
        print(f"🛑 Error: {e}")
        return 0

# Main execution
if __name__ == "__main__":
    print("\n" + "="*70)
    print("⚽ SCRAPING ALL SOCCER/FOOTBALL LEAGUES")
    print("="*70)
    print(f"\nTotal soccer leagues to scrape: {len(SOCCER_LEAGUES)}")
    print("This will take several minutes...\n")
    
    # Create summary
    summary = {
        "total_leagues": len(SOCCER_LEAGUES),
        "successful_leagues": 0,
        "total_teams": 0,
        "leagues": []
    }
    
    for i, league in enumerate(SOCCER_LEAGUES, 1):
        print(f"\n[{i}/{len(SOCCER_LEAGUES)}] Processing: {league}")
        
        teams_downloaded = download_league_logos(league)
        
        if teams_downloaded > 0:
            summary["successful_leagues"] += 1
            summary["total_teams"] += teams_downloaded
            summary["leagues"].append({
                "name": league,
                "teams": teams_downloaded
            })
        
        # Be polite to the API
        if i < len(SOCCER_LEAGUES):
            time.sleep(1.5)
    
    # Save summary
    with open("soccer_scraping_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*70)
    print("🎉 SOCCER SCRAPING COMPLETE!")
    print("="*70)
    print(f"✅ Successful leagues: {summary['successful_leagues']}/{summary['total_leagues']}")
    print(f"✅ Total teams downloaded: {summary['total_teams']}")
    print(f"\n📁 Logos saved in: soccer_logos/")
    print(f"📄 Data saved in: soccer_data/")
    print(f"📊 Summary saved: soccer_scraping_summary.json")
    print("="*70 + "\n")
