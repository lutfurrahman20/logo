import requests
import json
from pathlib import Path
import time

API_KEY = "3"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Comprehensive list of all baseball leagues
BASEBALL_LEAGUES = [
    # USA - Professional
    "MLB",
    "Minor League Baseball",
    "Triple-A",
    "Double-A",
    "High-A",
    "Low-A",
    
    # International - Professional
    "Nippon Professional Baseball",  # Japan
    "KBO League",  # Korea
    "Chinese Professional Baseball League",  # Taiwan
    "Mexican League",
    "Cuban National Series",
    "Dominican Professional Baseball League",
    "Venezuelan Professional Baseball League",
    "Puerto Rico Baseball League",
    "Colombian Professional Baseball League",
    "Nicaraguan Professional Baseball League",
    "Australian Baseball League",
    "Italian Baseball League",
    "Dutch Hoofdklasse",
    
    # Winter Leagues
    "Caribbean Series",
    "Arizona Fall League",
    "Dominican Winter League",
    "Mexican Pacific League",
    "Venezuelan Winter League",
    "Puerto Rican Winter League",
    "Colombian Winter League",
    
    # College/Amateur
    "NCAA Baseball",
    "College World Series",
    
    # European
    "European Baseball Championship",
    "German Baseball-Bundesliga",
    "Czech Extraliga",
    
    # Other
    "World Baseball Classic",
    "Baseball World Cup",
]

def download_league_logos(league_name):
    """Download all team logos for a specific league"""
    safe_league_name = league_name.lower().replace(" ", "_").replace(".", "").replace("-", "_")
    
    print(f"\n{'='*70}")
    print(f"⚾ {league_name}")
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
        json_folder = "baseball_data"
        Path(json_folder).mkdir(exist_ok=True)
        json_file = f"{json_folder}/{safe_league_name}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(teams, f, indent=2, ensure_ascii=False)
        
        # Download logos
        logos_folder = f"baseball_logos/{safe_league_name}"
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
    print("⚾ SCRAPING ALL BASEBALL LEAGUES")
    print("="*70)
    print(f"\nTotal baseball leagues to scrape: {len(BASEBALL_LEAGUES)}")
    print("This will take a few minutes...\n")
    
    # Create summary
    summary = {
        "total_leagues": len(BASEBALL_LEAGUES),
        "successful_leagues": 0,
        "total_teams": 0,
        "leagues": []
    }
    
    for i, league in enumerate(BASEBALL_LEAGUES, 1):
        print(f"\n[{i}/{len(BASEBALL_LEAGUES)}] Processing: {league}")
        
        teams_downloaded = download_league_logos(league)
        
        if teams_downloaded > 0:
            summary["successful_leagues"] += 1
            summary["total_teams"] += teams_downloaded
            summary["leagues"].append({
                "name": league,
                "teams": teams_downloaded
            })
        
        # Be polite to the API
        if i < len(BASEBALL_LEAGUES):
            time.sleep(1.5)
    
    # Save summary
    with open("baseball_scraping_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*70)
    print("🎉 BASEBALL SCRAPING COMPLETE!")
    print("="*70)
    print(f"✅ Successful leagues: {summary['successful_leagues']}/{summary['total_leagues']}")
    print(f"✅ Total teams downloaded: {summary['total_teams']}")
    print(f"\n📁 Logos saved in: baseball_logos/")
    print(f"📄 Data saved in: baseball_data/")
    print(f"📊 Summary saved: baseball_scraping_summary.json")
    print("="*70 + "\n")
