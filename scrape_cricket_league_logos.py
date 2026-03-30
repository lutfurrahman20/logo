import sys
import requests
import json
from pathlib import Path
import time

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

API_BASE = "https://www.thesportsdb.com/api/v1/json/3"

# ─────────────────────────────────────────────────────────────────────────────
# Full list of 59 target leagues with multi-source logo strategy:
#   tsdb_name   → exact name in thesportsdb (strLeague field)
#   wiki_files  → candidate filenames to try in Wikimedia Commons
#   direct_url  → confirmed public logo URL
# ─────────────────────────────────────────────────────────────────────────────
LEAGUES = [
    # ─── International / ACC / ICC ──────────────────────────────────────────
    {
        "name": "ACC - Asia Cup Women",
        "safe": "ACC_Asia_Cup_Women",
        "tsdb_name": None,
        "wiki_files": ["Asia_Cup_Women's_T20.svg", "Women's_Asia_Cup_T20.png",
                       "ACC_Women's_T20_Asia_Cup_logo.png"],
    },
    {
        "name": "ACC - T20 Asia Cup",
        "safe": "ACC_T20_Asia_Cup",
        "tsdb_name": None,
        "wiki_files": ["Asia Cup 2014 Logo \u2014 text only.svg",
                       "Asia cup logo 1997.jpg"],
    },
    {
        "name": "ICC - Champions Trophy",
        "safe": "ICC_Champions_Trophy",
        "tsdb_name": None,
        "wiki_files": ["2025 ICC Men's Champions Trophy Logo.svg",
                       "ICC-Champions-Trophy-2025-Logo.jpg"],
    },
    {
        "name": "ICC - CWC Challenge League",
        "safe": "ICC_CWC_Challenge_League",
        "tsdb_name": None,
        "wiki_files": ["ICC_Cricket_World_Cup_Challenge_League.svg",
                       "ICC_CWC_Challenge_League.png"],
    },
    {
        "name": "ICC - CWC Challenge League 2",
        "safe": "ICC_CWC_Challenge_League_2",
        "tsdb_name": None,
        "wiki_files": ["ICC_Cricket_World_Cup_Challenge_League_B.svg",
                       "ICC_CWC_Challenge_League_B.png"],
    },
    {
        "name": "ICC - T20 World Cup",
        "safe": "ICC_T20_World_Cup",
        "tsdb_name": None,
        "wiki_files": ["2024 ICC Men's T20 World Cup logo text only.png",
                       "ICC Men's T20 World Cup (2024) logo text only.png"],
    },
    {
        "name": "ICC - T20 World Cup Qualifiers",
        "safe": "ICC_T20_World_Cup_Qualifiers",
        "tsdb_name": None,
        "wiki_files": ["ICC_Men's_T20_World_Cup_Qualifier.png",
                       "ICC_T20_World_Cup_Qualifier.svg"],
    },
    {
        "name": "ICC - T20 World Cup Qualifiers Women",
        "safe": "ICC_T20_World_Cup_Qualifiers_Women",
        "tsdb_name": None,
        "wiki_files": ["2026 ICC Women's T20 World Cup logo text only.png",
                       "Women's T20 World Cup logo text only.png"],
    },
    {
        "name": "ICC - Test Championship",
        "safe": "ICC_Test_Championship",
        "tsdb_name": None,
        "wiki_files": ["ICC_World_Test_Championship.svg",
                       "ICC_World_Test_Championship_logo.svg",
                       "ICC_World_Test_Championship.png",
                       "World_Test_Championship_logo.svg"],
    },
    {
        "name": "ICC - World Cup Women",
        "safe": "ICC_World_Cup_Women",
        "tsdb_name": None,
        "wiki_files": ["2025 Women's Cricket World Cup logo text only.png",
                       "Women's Cricket World Cup Logo (cropped).png"],
    },
    {
        "name": "International - List A Tours",
        "safe": "International_List_A_Tours",
        "tsdb_name": None,
        "wiki_files": [],
    },
    {
        "name": "International - Tours",
        "safe": "International_Tours",
        "tsdb_name": None,
        "wiki_files": [],
    },
    {
        "name": "International - Tours Women",
        "safe": "International_Tours_Women",
        "tsdb_name": None,
        "wiki_files": [],
    },
    # ─── Afghanistan ────────────────────────────────────────────────────────
    {
        "name": "Afghanistan - Domestic T20",
        "safe": "Afghanistan_Domestic_T20",
        "tsdb_name": "Shpageeza Cricket League",
        "wiki_files": ["Shpageeza_Cricket_League_logo.png", "Afghanistan_Premier_League.svg"],
    },
    # ─── Australia ──────────────────────────────────────────────────────────
    {
        "name": "Australia - Big Bash League",
        "safe": "Australia_Big_Bash_League",
        "tsdb_name": "Australian Big Bash League",
        "wiki_files": ["Big_Bash_League_logo.svg", "BBL_Logo.png"],
    },
    {
        "name": "Australia - Big Bash League Women",
        "safe": "Australia_Big_Bash_League_Women",
        "tsdb_name": None,
        "wiki_files": ["Women's_Big_Bash_League.svg", "Women's_Big_Bash_League_logo.svg",
                       "WBBL_logo.svg", "WBBL_logo.png",
                       "Women's_Big_Bash_League_(logo).png"],
    },
    {
        "name": "Australia - Marsh One Day Cup",
        "safe": "Australia_Marsh_One_Day_Cup",
        "tsdb_name": None,
        "wiki_files": ["Marsh_One-Day_Cup.png", "Marsh_One_Day_Cup_logo.svg",
                       "One-Day_Cup_(Australia).png"],
    },
    {
        "name": "Australia - Sheffield Shield",
        "safe": "Australia_Sheffield_Shield",
        "tsdb_name": "Sheffield Shield",
        "wiki_files": ["Sheffield_Shield.svg", "Sheffield_Shield_logo.png"],
    },
    {
        "name": "Australia - WNCL",
        "safe": "Australia_WNCL",
        "tsdb_name": None,
        "wiki_files": ["Women's_National_Cricket_League.svg",
                       "WNCL_logo.png", "WNCL_2023_logo.png"],
    },
    # ─── Bangladesh ─────────────────────────────────────────────────────────
    {
        "name": "Bangladesh - BPL",
        "safe": "Bangladesh_BPL",
        "tsdb_name": "Bangladesh Premier League",
        "wiki_files": ["Bangladesh_Premier_League.svg", "BPL_logo.png"],
    },
    {
        "name": "Bangladesh - Dhaka Premier Division",
        "safe": "Bangladesh_Dhaka_Premier_Division",
        "tsdb_name": None,
        "wiki_files": ["Dhaka_Premier_Division_Cricket_League.svg",
                       "Dhaka_Premier_League.png"],
    },
    {
        "name": "Bangladesh - NCL T20",
        "safe": "Bangladesh_NCL_T20",
        "tsdb_name": None,
        "wiki_files": ["Bangladesh_National_Cricket_League.svg",
                       "BCB_NCL_T20.png"],
    },
    # ─── England ────────────────────────────────────────────────────────────
    {
        "name": "England - Charlotte Edwards Cup",
        "safe": "England_Charlotte_Edwards_Cup",
        "tsdb_name": None,
        "wiki_files": ["Charlotte_Edwards_Cup.svg", "Charlotte_Edwards_Cup_logo.png"],
    },
    {
        "name": "England - County Championship",
        "safe": "England_County_Championship",
        "tsdb_name": "English County Championship Division 1",
        "wiki_files": ["County_Championship.svg", "County_Championship_logo.png"],
    },
    {
        "name": "England - County Championship Division 2",
        "safe": "England_County_Championship_Division_2",
        "tsdb_name": "English County Championship Division 2",
        "wiki_files": [],
    },
    {
        "name": "England - One Day Cup",
        "safe": "England_One_Day_Cup",
        "tsdb_name": None,
        "wiki_files": ["Royal_London_One-Day_Cup.svg",
                       "Royal_London_One-Day_Cup_logo.png",
                       "One_Day_Cup_(cricket).png"],
    },
    {
        "name": "England - One Day Cup Women",
        "safe": "England_One_Day_Cup_Women",
        "tsdb_name": None,
        "wiki_files": ["Women's_One-Day_Cup_(cricket).png",
                       "Royal_London_Women's_One-Day_Cup.svg"],
    },
    {
        "name": "England - RHF Trophy",
        "safe": "England_RHF_Trophy",
        "tsdb_name": None,
        "wiki_files": ["RHF_Trophy.png", "RHF_Trophy_logo.svg"],
    },
    {
        "name": "England - T20 Blast",
        "safe": "England_T20_Blast",
        "tsdb_name": "English t20 Blast",
        "wiki_files": ["Vitality_Blast.svg", "T20_Blast_logo.png"],
    },
    {
        "name": "England - T20 Blast Women",
        "safe": "England_T20_Blast_Women",
        "tsdb_name": None,
        "wiki_files": ["Women's_T20_Blast.png", "ECB_Women's_T20_Blast.svg"],
    },
    {
        "name": "England - The Hundred",
        "safe": "England_The_Hundred",
        "tsdb_name": None,
        "wiki_files": ["The_Hundred_(cricket_competition).svg",
                       "The_Hundred_cricket_logo.svg",
                       "The_Hundred_logo.png",
                       "The_Hundred_(cricket).svg"],
    },
    {
        "name": "England - The Hundred Women",
        "safe": "England_The_Hundred_Women",
        "tsdb_name": None,
        "wiki_files": ["The_Hundred_Women's_Competition.svg",
                       "The_Hundred_Women.png",
                       "The_Hundred_Women's_competition_logo.png"],
    },
    # ─── India ──────────────────────────────────────────────────────────────
    {
        "name": "India - IPL",
        "safe": "India_IPL",
        "tsdb_name": "Indian Premier League",
        "wiki_files": ["Indian_Premier_League_Official_Logo.svg",
                       "IPL_logo.svg", "IPL_logo.png"],
    },
    {
        "name": "India - Ranji Trophy",
        "safe": "India_Ranji_Trophy",
        "tsdb_name": None,
        "wiki_files": ["Ranji_Trophy.svg", "Ranji_Trophy_logo.svg",
                       "Ranji_Trophy_Logo.png"],
    },
    {
        "name": "India - SMA Trophy",
        "safe": "India_SMA_Trophy",
        "tsdb_name": None,
        "wiki_files": ["SMA_Trophy.png", "SMA_Trophy_logo.svg"],
    },
    {
        "name": "India - Tamil Nadu Premier League",
        "safe": "India_Tamil_Nadu_Premier_League",
        "tsdb_name": None,
        "wiki_files": ["Tamil_Nadu_Premier_League.svg",
                       "TNPL_logo.png", "TNPL_2017.png"],
    },
    {
        "name": "India - Vijay Hazare Trophy",
        "safe": "India_Vijay_Hazare_Trophy",
        "tsdb_name": None,
        "wiki_files": ["Vijay_Hazare_Trophy.svg",
                       "Vijay_Hazare_Trophy_Logo.png",
                       "Vijay_Hazare_Trophy_logo.svg"],
    },
    {
        "name": "India - WPL",
        "safe": "India_WPL",
        "tsdb_name": None,
        "wiki_files": ["WPL.png"],
    },
    # ─── Ireland ────────────────────────────────────────────────────────────
    {
        "name": "Ireland - Inter Provincial T20",
        "safe": "Ireland_Inter_Provincial_T20",
        "tsdb_name": "Cricket Ireland Inter-Provincial T20 Trophy",
        "wiki_files": ["Cricket_Ireland_Inter-Provincial_T20_Trophy.svg"],
    },
    # ─── New Zealand ────────────────────────────────────────────────────────
    {
        "name": "New Zealand - Ford Trophy",
        "safe": "New_Zealand_Ford_Trophy",
        "tsdb_name": None,
        "wiki_files": ["Ford_Trophy_(cricket).svg",
                       "Ford_Trophy.svg", "Ford_Trophy.png",
                       "Ford_Trophy_logo.png"],
    },
    {
        "name": "New Zealand - Plunket Shield",
        "safe": "New_Zealand_Plunket_Shield",
        "tsdb_name": None,
        "wiki_files": ["Plunket_Shield.svg", "Plunket_Shield.jpg",
                       "Plunket_Shield.png"],
    },
    {
        "name": "New Zealand - Super Smash",
        "safe": "New_Zealand_Super_Smash",
        "tsdb_name": "New Zealand Super Smash",
        "wiki_files": ["Super_Smash_(cricket).svg", "Super_Smash_logo.png"],
    },
    {
        "name": "New Zealand - Super Smash Women",
        "safe": "New_Zealand_Super_Smash_Women",
        "tsdb_name": None,
        "wiki_files": ["Women's_Super_Smash.svg", "Women's_Super_Smash.png",
                       "Super_Smash_Women.png"],
    },
    # ─── Pakistan ───────────────────────────────────────────────────────────
    {
        "name": "Pakistan - National T20 Cup",
        "safe": "Pakistan_National_T20_Cup",
        "tsdb_name": None,
        "wiki_files": ["Pakistan_National_T20_Cup.svg",
                       "National_T20_Cup_logo.png",
                       "PCB_National_T20_Cup.svg"],
    },
    {
        "name": "Pakistan - Super League",
        "safe": "Pakistan_Super_League",
        "tsdb_name": "Pakistan Super League",
        "wiki_files": ["Pakistan_Super_League.svg",
                       "Pakistan_Super_League_logo.svg",
                       "PSL_logo.png"],
    },
    # ─── South Africa ───────────────────────────────────────────────────────
    {
        "name": "South Africa - CSA Four Day",
        "safe": "South_Africa_CSA_Four_Day",
        "tsdb_name": None,
        "wiki_files": ["CSA_4-Day_Franchise_Series.svg",
                       "CSA_Four_Day_Cup.png",
                       "CSA_Provincial_Four_Day_Competition.svg"],
    },
    {
        "name": "South Africa - CSA One Day",
        "safe": "South_Africa_CSA_One_Day",
        "tsdb_name": None,
        "wiki_files": ["CSA_One-Day_Challenge.svg",
                       "CSA_Provincial_One_Day_Challenge.svg",
                       "CSA_One_Day_Cup.png"],
    },
    {
        "name": "South Africa - CSA Pro20 Women",
        "safe": "South_Africa_CSA_Pro20_Women",
        "tsdb_name": None,
        "wiki_files": ["CSA_Women's_Provincial_T20.svg",
                       "CSA_Pro20_Women.png"],
    },
    {
        "name": "South Africa - SA20",
        "safe": "South_Africa_SA20",
        "tsdb_name": "SA20",
        "wiki_files": ["SA20Logo.png", "SA20_logo.svg"],
    },
    # ─── Sri Lanka ──────────────────────────────────────────────────────────
    {
        "name": "Sri Lanka - Lanka Premier League",
        "safe": "Sri_Lanka_Lanka_Premier_League",
        "tsdb_name": "Lanka Premier League",
        "wiki_files": ["Lanka_Premier_League.svg", "LPL_logo.png"],
    },
    {
        "name": "Sri Lanka - Premier Trophy",
        "safe": "Sri_Lanka_Premier_Trophy",
        "tsdb_name": None,
        "wiki_files": ["Sri_Lanka_Premier_Trophy.svg",
                       "SLC_Premier_Trophy.png"],
    },
    {
        "name": "Sri Lanka - Super League Four Day",
        "safe": "Sri_Lanka_Super_League_Four_Day",
        "tsdb_name": None,
        "wiki_files": ["Sri_Lanka_Super_Four_Day_Tournament.svg",
                       "SLC_Super_League.png"],
    },
    {
        "name": "Sri Lanka - T20 Major Clubs",
        "safe": "Sri_Lanka_T20_Major_Clubs",
        "tsdb_name": None,
        "wiki_files": ["Sri_Lanka_T20_Major_Clubs.svg",
                       "SLC_T20_Major_Clubs.png"],
    },
    # ─── USA ────────────────────────────────────────────────────────────────
    {
        "name": "USA - Major League Cricket",
        "safe": "USA_Major_League_Cricket",
        "tsdb_name": None,
        "wiki_files": ["Major_League_Cricket_logo.svg",
                       "Major_League_Cricket.svg",
                       "Major_League_Cricket_logo.png"],
    },
    # ─── West Indies ────────────────────────────────────────────────────────
    {
        "name": "West Indies - 4Day Championship",
        "safe": "West_Indies_4Day_Championship",
        "tsdb_name": None,
        "wiki_files": ["West_Indies_4-Day_Championship.svg",
                       "CWI_Regional_4_Day.png",
                       "West_Indies_4_Day_Championship.png"],
    },
    {
        "name": "West Indies - Caribbean Premier League",
        "safe": "West_Indies_Caribbean_Premier_League",
        "tsdb_name": "Caribbean Premier League",
        "wiki_files": ["Caribbean_Premier_League.svg", "CPL_logo.png"],
    },
    {
        "name": "West Indies - Caribbean Premier League Women",
        "safe": "West_Indies_Caribbean_Premier_League_Women",
        "tsdb_name": None,
        "wiki_files": ["Women's_Caribbean_Premier_League.svg",
                       "Women's_CPL.png",
                       "Women's_Caribbean_Premier_League_logo.png"],
    },
    # ─── Zimbabwe ───────────────────────────────────────────────────────────
    {
        "name": "Zimbabwe - Domestic T20",
        "safe": "Zimbabwe_Domestic_T20",
        "tsdb_name": "Zimbabwean Domestic Twenty20",
        "wiki_files": ["Zimbabwe_T20_Tri_Series.svg",
                       "Zimbabwean_Domestic_T20.png"],
    },
    {
        "name": "Zimbabwe - Logan Cup",
        "safe": "Zimbabwe_Logan_Cup",
        "tsdb_name": None,
        "wiki_files": ["Logan_Cup.svg", "Logan_Cup_logo.png",
                       "Logan_Cup_(Zimbabwe).svg"],
    },
    {
        "name": "Zimbabwe - Pro50",
        "safe": "Zimbabwe_Pro50",
        "tsdb_name": None,
        "wiki_files": ["Zimbabwe_Pro50.svg", "Zimbabwe_Pro50_Championship.png",
                       "Pro50_Championship.svg"],
    },
]


def get_tsdb_logo(tsdb_name):
    """Fetch logo URL from thesportsdb by league name."""
    # Search globally
    url = f"{API_BASE}/search_all_leagues.php?s=Cricket"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            for league in (r.json().get("countries") or []):
                if league.get("strLeague", "").strip() == tsdb_name:
                    return league.get("strBadge") or league.get("strLogo")
    except Exception:
        pass

    # Per-country search
    countries = [
        "Australia", "India", "England", "Pakistan", "Sri Lanka",
        "South Africa", "New Zealand", "Bangladesh", "West Indies",
        "Zimbabwe", "Afghanistan", "Ireland", "UAE", "USA",
    ]
    for country in countries:
        encoded = country.replace(" ", "%20")
        try:
            r = requests.get(
                f"{API_BASE}/search_all_leagues.php?c={encoded}&s=Cricket",
                headers=HEADERS, timeout=10,
            )
            if r.status_code == 200:
                for league in (r.json().get("countries") or []):
                    if league.get("strLeague", "").strip() == tsdb_name:
                        return league.get("strBadge") or league.get("strLogo")
        except Exception:
            pass
        time.sleep(0.15)
    return None


def get_wikimedia_url(filename):
    """Resolve a Wikimedia Commons file to its full image URL via imageinfo API."""
    title = f"File:{filename}"
    api_url = (
        "https://commons.wikimedia.org/w/api.php"
        f"?action=query&titles={requests.utils.quote(title)}&prop=imageinfo"
        "&iiprop=url&format=json"
    )
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        pages = r.json().get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1":
                continue
            for info in page.get("imageinfo", []):
                url = info.get("url")
                if url:
                    return url
    except Exception:
        pass
    return None


def download_image(url, filepath):
    """Download image from URL to filepath."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200 and len(r.content) > 500:
            with open(filepath, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Pre-cache thesportsdb cricket leagues (all countries) once at startup
# ─────────────────────────────────────────────────────────────────────────────
def build_tsdb_cache():
    cache = {}
    COUNTRIES = [
        "", "Australia", "India", "England", "Pakistan", "Sri Lanka",
        "South Africa", "New Zealand", "Bangladesh", "West Indies",
        "Zimbabwe", "Afghanistan", "Ireland", "UAE", "USA",
    ]
    for country in COUNTRIES:
        if country:
            url = f"{API_BASE}/search_all_leagues.php?c={country.replace(' ', '%20')}&s=Cricket"
        else:
            url = f"{API_BASE}/search_all_leagues.php?s=Cricket"
        try:
            r = requests.get(url, headers=HEADERS, timeout=12)
            if r.status_code == 200:
                for league in (r.json().get("countries") or []):
                    name = league.get("strLeague", "").strip()
                    logo_url = league.get("strBadge") or league.get("strLogo")
                    if name and logo_url:
                        cache[name] = logo_url
        except Exception:
            pass
        time.sleep(0.25)
    return cache


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🏏 DOWNLOADING CRICKET LEAGUE LOGOS – 59 LEAGUES")
    print("="*70)

    output_dir = Path("cricket_league_logos")
    output_dir.mkdir(exist_ok=True)

    # ── Step 1: Build thesportsdb cache ────────────────────────────────────
    print("\n[Step 1] Loading thesportsdb cricket league data...", flush=True)
    tsdb_cache = build_tsdb_cache()
    print(f"  Cached {len(tsdb_cache)} leagues from thesportsdb")

    # ── Step 2: Process each target league ─────────────────────────────────
    print(f"\n[Step 2] Downloading logos for {len(LEAGUES)} leagues...\n")

    downloaded = 0
    not_found = []
    results = []

    for league in LEAGUES:
        name       = league["name"]
        safe       = league["safe"]
        tsdb_name  = league.get("tsdb_name")
        wiki_files = league.get("wiki_files", [])

        print(f"  {name}", end=" ... ", flush=True)

        logo_url = None
        source   = None

        # --- Priority 1: thesportsdb cache ---
        if tsdb_name and tsdb_name in tsdb_cache:
            logo_url = tsdb_cache[tsdb_name]
            source   = f"thesportsdb ({tsdb_name})"

        # --- Priority 2: Wikimedia Commons file lookup ---
        if not logo_url:
            for wf in wiki_files:
                wurl = get_wikimedia_url(wf)
                if wurl:
                    logo_url = wurl
                    source   = f"wikimedia ({wf})"
                    break
                time.sleep(0.15)

        if not logo_url:
            print("⚠️ not found")
            not_found.append(name)
            continue

        # Determine file extension
        ext = logo_url.split(".")[-1].split("?")[0].lower()
        if ext not in ("png", "jpg", "jpeg", "svg", "webp"):
            ext = "png"
        filepath = output_dir / f"{safe}.{ext}"

        if filepath.exists():
            print(f"⏭️  already exists ({source})")
            downloaded += 1
            results.append({"name": name, "source": source, "url": logo_url, "file": str(filepath)})
            continue

        if download_image(logo_url, filepath):
            print(f"✅ {filepath.name}  [{source}]")
            downloaded += 1
            results.append({"name": name, "source": source, "url": logo_url, "file": str(filepath)})
        else:
            print(f"❌ download failed ({logo_url[:60]}...)")
            not_found.append(name)

        time.sleep(0.2)

    # ── Summary ─────────────────────────────────────────────────────────────
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"  Total leagues targeted  : {len(LEAGUES)}")
    print(f"  Logos downloaded        : {downloaded}")
    print(f"  Not found / failed      : {len(not_found)}")
    if not_found:
        print("\n  Could not find logos for:")
        for n in not_found:
            print(f"    ⚠️  {n}")

    print("\n  Downloaded:")
    for r in results:
        print(f"    ✅ {r['name']}  [{r['source']}]")

    summary = {
        "total_targeted": len(LEAGUES),
        "downloaded": downloaded,
        "not_found_count": len(not_found),
        "results": results,
        "not_found": not_found,
    }
    with open("cricket_league_logos_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Done! Logos saved to '{output_dir}/'")
    print(f"📄 Results saved to 'cricket_league_logos_results.json'")
