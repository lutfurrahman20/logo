import sys
import requests
import json
from pathlib import Path
import time

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ESPN slug + display name for soccer leagues
# ESPN API: https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard
SOCCER_LEAGUES = [
    # England
    {"slug": "eng.1",          "name": "English Premier League"},
    {"slug": "eng.2",          "name": "English Championship"},
    {"slug": "eng.3",          "name": "English League One"},
    {"slug": "eng.4",          "name": "English League Two"},
    {"slug": "eng.fa",         "name": "English FA Cup"},
    {"slug": "eng.league_cup", "name": "English League Cup"},

    # Spain
    {"slug": "esp.1",     "name": "Spanish La Liga"},
    {"slug": "esp.2",     "name": "Spanish La Liga 2"},
    {"slug": "esp.copa",  "name": "Spanish Copa del Rey"},

    # Germany
    {"slug": "ger.1",     "name": "German Bundesliga"},
    {"slug": "ger.2",     "name": "German 2. Bundesliga"},
    {"slug": "ger.dfb",   "name": "German DFB Pokal"},

    # Italy
    {"slug": "ita.1",     "name": "Italian Serie A"},
    {"slug": "ita.2",     "name": "Italian Serie B"},
    {"slug": "ita.coppa", "name": "Italian Coppa Italia"},

    # France
    {"slug": "fra.1",     "name": "French Ligue 1"},
    {"slug": "fra.2",     "name": "French Ligue 2"},
    {"slug": "fra.coupe", "name": "French Coupe de France"},

    # Netherlands
    {"slug": "ned.1", "name": "Dutch Eredivisie"},
    {"slug": "ned.2", "name": "Dutch Eerste Divisie"},

    # Portugal
    {"slug": "por.1", "name": "Portuguese Primeira Liga"},
    {"slug": "por.2", "name": "Portuguese Segunda Liga"},

    # Scotland
    {"slug": "sco.1", "name": "Scottish Premiership"},
    {"slug": "sco.2", "name": "Scottish Championship"},

    # UEFA Competitions
    {"slug": "uefa.champions",   "name": "UEFA Champions League"},
    {"slug": "uefa.europa",      "name": "UEFA Europa League"},
    {"slug": "uefa.europa.conf", "name": "UEFA Conference League"},

    # Other European
    {"slug": "tur.1", "name": "Turkish Super Lig"},
    {"slug": "bel.1", "name": "Belgian Pro League"},
    {"slug": "gre.1", "name": "Greek Super League"},
    {"slug": "rus.1", "name": "Russian Premier League"},
    {"slug": "ukr.1", "name": "Ukrainian Premier League"},
    {"slug": "sui.1", "name": "Swiss Super League"},
    {"slug": "den.1", "name": "Danish Superliga"},
    {"slug": "nor.1", "name": "Norwegian Eliteserien"},
    {"slug": "swe.1", "name": "Swedish Allsvenskan"},
    {"slug": "pol.1", "name": "Polish Ekstraklasa"},
    {"slug": "cze.1", "name": "Czech First League"},
    {"slug": "rou.1", "name": "Romanian Liga I"},

    # Americas
    {"slug": "usa.1", "name": "MLS"},
    {"slug": "mex.1", "name": "Mexican Liga MX"},
    {"slug": "arg.1", "name": "Argentine Primera Division"},
    {"slug": "bra.1", "name": "Brazilian Serie A"},
    {"slug": "bra.2", "name": "Brazilian Serie B"},
    {"slug": "chi.1", "name": "Chilean Primera Division"},
    {"slug": "col.1", "name": "Colombian Primera A"},
    {"slug": "ecu.1", "name": "Ecuadorian Serie A"},
    {"slug": "per.1", "name": "Peruvian Primera Division"},
    {"slug": "uru.1", "name": "Uruguayan Primera Division"},

    # Asia & Oceania
    {"slug": "jpn.1", "name": "Japanese J League"},
    {"slug": "jpn.2", "name": "Japanese J2 League"},
    {"slug": "chn.1", "name": "Chinese Super League"},
    {"slug": "kor.1", "name": "Korean K League 1"},
    {"slug": "ind.1", "name": "Indian Super League"},
    {"slug": "sau.1", "name": "Saudi Pro League"},
    {"slug": "qat.1", "name": "Qatar Stars League"},
    {"slug": "uae.1", "name": "UAE Pro League"},
    {"slug": "tha.1", "name": "Thai Premier League"},
    {"slug": "aus.1", "name": "Australian A-League"},

    # Africa
    {"slug": "egy.1", "name": "Egyptian Premier League"},
    {"slug": "rsa.1", "name": "South African Premier League"},
    {"slug": "nga.1", "name": "Nigerian Premier League"},
]


def get_league_logo_from_espn(slug):
    """Fetch league logo URL from ESPN public API using league slug."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return None
        data = response.json()
        leagues = data.get("leagues", [])
        if not leagues:
            return None
        logos = leagues[0].get("logos", [])
        if logos:
            return logos[0].get("href")
    except Exception as e:
        print(f"  Error: {e}")
    return None


def download_image(url, filepath):
    """Download image from URL to filepath."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 100:
            with open(filepath, "wb") as f:
                f.write(r.content)
            return True
    except:
        pass
    return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("⚽ DOWNLOADING SOCCER LEAGUE LOGOS (ESPN)")
    print("="*70)

    output_dir = Path("soccer_league_logos")
    output_dir.mkdir(exist_ok=True)

    downloaded = 0
    failed = []
    results = []

    for league in SOCCER_LEAGUES:
        slug = league["slug"]
        league_name = league["name"]

        print(f"\n🔍 {league_name} ({slug})", end=" ... ")

        logo_url = get_league_logo_from_espn(slug)

        if logo_url:
            ext = logo_url.split(".")[-1].split("?")[0]
            if ext.lower() not in ["png", "jpg", "jpeg", "webp", "svg"]:
                ext = "png"
            safe_name = league_name.replace(" ", "_").replace("/", "_").replace(".", "").replace("-", "_")
            filename = f"{safe_name}.{ext}"
            filepath = output_dir / filename

            if download_image(logo_url, filepath):
                print(f"✅ Saved: {filename}")
                downloaded += 1
                results.append({"name": league_name, "slug": slug, "logo_url": logo_url, "file": str(filepath)})
            else:
                print(f"❌ Download failed")
                failed.append(league_name)
        else:
            print(f"⚠️  No logo found")
            failed.append(league_name)

        time.sleep(0.3)

    print("\n" + "="*70)
    print(f"✅ Downloaded: {downloaded} logos")
    print(f"❌ Failed/Not found: {len(failed)}")
    if failed:
        print("Failed leagues:")
        for f in failed:
            print(f"  - {f}")
    print(f"\n📁 Logos saved in: soccer_league_logos/")
    print("="*70)

    with open("soccer_league_logos_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("📄 Results saved: soccer_league_logos_results.json\n")
