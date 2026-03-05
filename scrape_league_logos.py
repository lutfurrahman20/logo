import requests
import json
from pathlib import Path
import time

API_KEY = "3"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# List of all sports to get leagues from
SPORTS = [
    "Soccer",
    "Basketball",
    "American Football",
    "Ice Hockey",
    "Baseball",
    "Rugby",
    "Cricket",
    "Tennis",
    "Golf",
    "Motorsport",
    "Fighting",
    "Aussie Rules",
    "Handball",
    "Volleyball",
    "Athletics",
    "Swimming",
    "Cycling",
    "Darts",
    "Snooker",
]

def get_leagues_by_sport(sport):
    """Get all leagues for a specific sport"""
    url = f"https://www.thesportsdb.com/api/v1/json/{API_KEY}/search_all_leagues.php?s={sport.replace(' ', '%20')}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data and data.get("countries"):
                return data["countries"]
    except:
        pass
    return []

def download_league_logo(league_info, logos_folder):
    """Download a single league logo"""
    league_name = league_info.get("strLeague")
    league_badge = league_info.get("strBadge")
    league_logo = league_info.get("strLogo")
    
    # Try badge first, then logo
    logo_url = league_badge or league_logo
    
    if not logo_url:
        return False
    
    safe_name = league_name.replace(" ", "_").replace("/", "_").replace(".", "").replace("-", "_")
    extension = logo_url.split(".")[-1].split("?")[0]
    filename = f"{safe_name}.{extension}"
    filepath = f"{logos_folder}/{filename}"
    
    try:
        r = requests.get(logo_url, timeout=10)
        if r.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(r.content)
            return True
    except:
        pass
    return False

# Main execution
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🏆 SCRAPING ALL LEAGUE LOGOS FROM THESPORTSDB")
    print("="*70)
    print("\nFetching leagues from all sports...\n")
    
    # Create output folders
    logos_folder = "league_logos"
    Path(logos_folder).mkdir(exist_ok=True)
    
    all_leagues = []
    total_logos_downloaded = 0
    
    for sport in SPORTS:
        print(f"\n{'='*70}")
        print(f"📋 {sport}")
        print(f"{'='*70}")
        
        leagues = get_leagues_by_sport(sport)
        
        if not leagues:
            print(f"⚠️  No leagues found")
            continue
        
        print(f"✅ Found {len(leagues)} leagues")
        
        sport_success = 0
        for league_info in leagues:
            league_name = league_info.get("strLeague")
            league_id = league_info.get("idLeague")
            sport_name = league_info.get("strSport")
            country = league_info.get("strCountry")
            
            # Store league info
            league_data = {
                "id": league_id,
                "name": league_name,
                "sport": sport_name,
                "country": country,
                "badge": league_info.get("strBadge"),
                "logo": league_info.get("strLogo"),
            }
            all_leagues.append(league_data)
            
            # Download logo
            if download_league_logo(league_info, logos_folder):
                print(f"  ✅ {league_name}")
                sport_success += 1
                total_logos_downloaded += 1
            else:
                print(f"  ⚠️  {league_name} (no logo)")
        
        print(f"💾 Downloaded {sport_success} logos from {sport}")
        time.sleep(1)
    
    # Save all league data to JSON
    with open("all_leagues_data.json", "w", encoding="utf-8") as f:
        json.dump(all_leagues, f, indent=2, ensure_ascii=False)
    
    # Create summary
    summary = {
        "total_leagues": len(all_leagues),
        "total_logos_downloaded": total_logos_downloaded,
        "sports_count": len(SPORTS),
        "by_sport": {}
    }
    
    # Count by sport
    for league in all_leagues:
        sport = league["sport"]
        if sport not in summary["by_sport"]:
            summary["by_sport"][sport] = 0
        summary["by_sport"][sport] += 1
    
    with open("league_logos_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*70)
    print("🎉 LEAGUE LOGO SCRAPING COMPLETE!")
    print("="*70)
    print(f"✅ Total leagues found: {len(all_leagues)}")
    print(f"✅ Total logos downloaded: {total_logos_downloaded}")
    print(f"\n📁 Logos saved in: {logos_folder}/")
    print(f"📄 Full data: all_leagues_data.json")
    print(f"📊 Summary: league_logos_summary.json")
    print("="*70 + "\n")
    
    # Show breakdown by sport
    print("\nBreakdown by Sport:")
    print("-" * 40)
    for sport, count in sorted(summary["by_sport"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {sport}: {count} leagues")
    print()
