import sys
import requests
import json
from pathlib import Path
import time
import re
from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding="utf-8")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Exact league names requested by user
LEAGUES_TO_FIND = [
    "AFC - Asian Cup Women",
    "AFC - Asian Cup Women Qualifiers",
    "AFC - Challenge League",
    "AFC - Champions League",
    "AFC - Champions League 2",
    "ASEAN - Club Championship",
    "Albania - Kategoria Superiore",
    "Albania - Kategoria e Pare",
    "Albania - Kupa e Shqiperise",
    "Algeria - Cup",
    "Algeria - Ligue 1",
    "Algeria - Ligue 2",
    "Andorra - Copa Constitucio",
    "Andorra - Primera Divisio",
    "Andorra - Segona Divisio",
    "Angola - Girabola",
    "Argentina - Copa Argentina",
    "Argentina - Primera Division",
    "Argentina - Primera Nacional",
    "Armenia - 1st League",
    "Armenia - Cup",
    "Armenia - Premier League",
    "Australia - A-League",
    "Australia - A-League Women",
    "Australia - Capital NPL",
    "Australia - Championship",
    "Australia - Cup",
    "Australia - NSW NPL",
    "Australia - Northern NSW NPL",
    "Australia - Queensland NPL",
    "Australia - Queensland Premier League",
    "Australia - South Australia NPL",
    "Australia - Tasmania NPL",
    "Australia - Victoria NPL",
    "Australia - Victoria Premier League 1",
    "Austria - 2. Liga",
    "Austria - Bundesliga",
    "Austria - OFB Cup",
    "Azerbaijan - 1st Division",
    "Azerbaijan - Cup",
    "Azerbaijan - Premier League",
    "Bahrain - Premier League",
    "Belarus - Cup",
    "Belarus - Pervaya League",
    "Belarus - Premier League",
    "Belgium - Challenger Pro League",
    "Belgium - Cup",
    "Belgium - Jupiler Pro League",
    "Belgium - Womens Super League",
    "Bolivia - Division Professional",
    "Bosnia and Herzegovina - Cup",
    "Bosnia and Herzegovina - Premier League",
    "Bosnia and Herzegovina - Prva Liga",
    "Brazil - Amapaense",
    "Brazil - Baiano",
    "Brazil - Baiano 2",
    "Brazil - Capixaba",
    "Brazil - Carioca",
    "Brazil - Catarinense",
    "Brazil - Cearense",
    "Brazil - Copa do Brasil",
    "Brazil - Gaucho",
    "Brazil - Gaucho 2",
    "Brazil - Gaucho 3",
    "Brazil - Goiano",
    "Brazil - Kings League",
    "Brazil - Mineiro I",
    "Brazil - Paraense",
    "Brazil - Paranaense",
    "Brazil - Serie A",
    "Brazil - Serie B",
    "Brazil - Serie C",
    "Brazil - Serie D",
    "Bulgaria - Cup",
    "Bulgaria - Parva Liga",
    "Bulgaria - Vtora Liga",
    "CAF - Africa Cup of Nations",
    "CAF - Africa Cup of Nations Qualifiers",
    "CAF - African Nations Championship",
    "CAFA - Nations Cup",
    "CECAFA - Clubs Cup",
    "CONCACAF - Caribbean Cup",
    "CONCACAF - Central America Cup",
    "CONCACAF - Champions Cup",
    "CONCACAF - Champions Cup Women",
    "CONCACAF - Gold Cup",
    "CONCACAF - Nations League",
    "CONMEBOL - Copa America",
    "CONMEBOL - Copa America Women",
    "CONMEBOL - Copa Libertadores",
    "CONMEBOL - Copa Sudamericana",
    "CONMEBOL - Nations League",
    "CONMEBOL - Nations League Women",
    "COSAFA - Cup",
    "Canada - Championship",
    "Canada - Premier League",
    "Canada - Soccer League",
    "Chile - Cup",
    "Chile - Primera B",
    "Chile - Primera Division",
    "China - FA Cup",
    "China - League One",
    "China - League Two",
    "China - Super League",
    "Colombia - Cup",
    "Colombia - Primera A",
    "Colombia - Primera B",
    "Costa Rica - Cup",
    "Costa Rica - Liga de Ascenso",
    "Costa Rica - Primera Division",
    "Croatia - 1. HNL",
    "Croatia - Cup",
    "Croatia - First NL",
    "Cyprus - Cup",
    "Cyprus - First Division",
    "Cyprus - Second Division",
    "Cyprus - Third Division",
    "Czech Republic - CFL",
    "Czech Republic - Cup",
    "Czech Republic - FNL",
    "Czech Republic - First League",
    "Czech Republic - MSFL",
    "Denmark - 1st Division",
    "Denmark - 2nd Division",
    "Denmark - DBU Pokalen",
    "Denmark - Superliga",
    "Ecuador - Cup",
    "Ecuador - Serie A",
    "Ecuador - Serie B",
    "Egypt - Cup",
    "Egypt - Premier League",
    "Egypt - Second Division",
    "El Salvador - Primera Division",
    "England - Championship",
    "England - Community Shield",
    "England - EFL Cup",
    "England - EFL Trophy",
    "England - FA Cup",
    "England - FA Trophy",
    "England - League 1",
    "England - League 2",
    "England - National League",
    "England - Premier League",
    "England - Womens Super League",
    "Estonia - Cup",
    "Estonia - Esiliiga",
    "Estonia - Esiliiga B",
    "Estonia - Meistriliiga Women",
    "Estonia - Premium Liiga",
    "Ethiopia - Premier League",
    "Ethiopia - Premier League Women",
    "FIFA - Arab Nations Cup",
    "FIFA - Club World Cup",
    "FIFA - Intercontinental Cup",
    "FIFA - World Cup",
    "FIFA - World Cup Qualifiers",
    "FIFA - World Cup U20",
    "FIFA - World Cup Women",
    "Faroe Islands - 1. Deild",
    "Faroe Islands - Cup",
    "Faroe Islands - Premier League",
    "Finland - Kakkonen",
    "Finland - Kolmonen",
    "Finland - Suomen Cup",
    "Finland - Veikkausliiga",
    "Finland - Ykkonen",
    "Finland - Ykkosliiga",
    "France - Coupe de France",
    "France - Ligue 1",
    "France - Ligue 2",
    "France - National 1",
    "France - Premiere Ligue",
    "France - Super Cup",
    "Georgia - Cup",
    "Georgia - Erovnuli Liga",
    "Georgia - Erovnuli Liga 2",
    "Germany - Bundesliga",
    "Germany - Bundesliga 2",
    "Germany - Bundesliga 3",
    "Germany - DFB Pokal",
    "Germany - Frauen Bundesliga",
    "Germany - Kings League",
    "Germany - Super Cup",
    "Gibraltar - Football League",
    "Gibraltar - Rock Cup",
    "Greece - Cup",
    "Greece - Super League",
    "Greece - Super League 2",
    "Guatemala - Liga Nacional",
    "Guatemala - Primera Division",
    "Hong Kong - Premier League",
    "Hungary - Maygar Kupa",
    "Hungary - NB I",
    "Hungary - NB II",
    "Hungary - NB III",
    "Iceland - 1. Deild",
    "Iceland - 1. Deild Women",
    "Iceland - 2. Deild",
    "Iceland - 3. Deild",
    "Iceland - 4. Deild",
    "Iceland - Besta Deild Karla",
    "Iceland - Besta Deild Women",
    "Iceland - Football Cup",
    "India - Calcutta Premier Division",
    "India - Durand Cup",
    "India - League 1",
    "India - League 2",
    "India - Super League",
    "Indonesia - Liga 1",
    "International - Club Friendlies",
    "International - Friendlies",
    "International - Friendlies Women",
    "International - Kings Cup",
    "Iraq - Stars League",
    "Ireland - Division 1",
    "Ireland - FAI Cup",
    "Ireland - Premier League",
    "Israel - Cup",
    "Israel - National League",
    "Israel - Premier League",
    "Italy - Coppa Italia",
    "Italy - Kings League",
    "Italy - Serie A",
    "Italy - Serie A Femminile",
    "Italy - Serie B",
    "Italy - Serie C",
    "Italy - Supercoppa",
    "Jamaica - Premier League",
    "Japan - Emperor Cup",
    "Japan - J1 League",
    "Japan - J2 League",
    "Japan - J3 League",
    "Japan - League Cup",
    "Kazakhstan - Cup",
    "Kazakhstan - First Division",
    "Kazakhstan - Premier League",
    "Kenya - Premier League",
    "Kings League - Club World Cup",
    "Kings League - World Cup",
    "Korea - Cup",
    "Korea - K1 League",
    "Korea - K2 League",
    "Korea - K3 League",
    "Korea - WK League",
    "Kosovo - First League",
    "Kosovo - Kupe e Kosoves",
    "Kosovo - Liga e Dyte",
    "Kosovo - Superliga",
    "Latvia - 1. Liga",
    "Latvia - Cup",
    "Latvia - Virsliga",
    "Lebanon - Premier League",
    "Liechtenstein - Aktiv Cup",
    "Lithuania - 1 Lyga",
    "Lithuania - 2 Lyga",
    "Lithuania - A Lyga",
    "Lithuania - Cup",
    "Luxembourg - 1. Division",
    "Luxembourg - Coupe",
    "Luxembourg - Promotion d Honneur",
    "Malaysia - Super League",
    "Malta - Challenge League",
    "Malta - FA Trophy",
    "Malta - Premier League",
    "Mexico - Liga MX",
    "Mexico - Liga MX Women",
    "Mexico - Liga Premier Serie A",
    "Mexico - Liga de Expansion MX",
    "Moldova - Cupa",
    "Moldova - Liga 1",
    "Moldova - Super Liga",
    "Mongolia - Premier League",
    "Montenegro - CFL 1",
    "Montenegro - CFL 2",
    "Montenegro - Cup Crne Gore",
    "Netherlands - Eerste Divisie",
    "Netherlands - Eredivisie",
    "Netherlands - KNVB Beker",
    "Netherlands - Super Cup",
    "Netherlands - Tweede Divisie",
    "Netherlands - Vrouwen Eredivisie",
    "New Zealand - National League",
    "North America - Leagues Cup",
    "North Macedonia - Cup",
    "North Macedonia - First League",
    "North Macedonia - Second League",
    "Northern Ireland - Championship",
    "Northern Ireland - Premiership",
    "Norway - 1. Divisjon",
    "Norway - 2. Division",
    "Norway - Eliteserien",
    "Norway - NM Cup",
    "Norway - Topserien Women",
    "Olympics Soccer Men",
    "Olympics Soccer Women",
    "Panama - Liga Panamena",
    "Panama - Liga Prom",
    "Paraguay - Primera Division",
    "Peru - Copa Peru",
    "Peru - Primera Division",
    "Peru - Segunda Division",
    "Poland - Cup",
    "Poland - Ekstraklasa",
    "Poland - I Liga",
    "Poland - II Liga",
    "Portugal - League Cup",
    "Portugal - Liga 3",
    "Portugal - Primeira Liga",
    "Portugal - Segunda Liga",
    "Portugal - Super Cup",
    "Portugal - Taca de Portugal",
    "Qatar - Stars League",
    "Romania - Cupa Romaniei",
    "Romania - Liga I",
    "Romania - Liga II",
    "Russia - Cup",
    "Russia - First League",
    "Russia - Premier League",
    "Russia - Second League A",
    "Russia - Super Cup",
    "San Marino - Campionato",
    "San Marino - Coppa Titano",
    "Saudi Arabia - Division 1",
    "Saudi Arabia - Kings Cup",
    "Saudi Arabia - Saudi League",
    "Scotland - Challenge Cup",
    "Scotland - Championship",
    "Scotland - League Cup",
    "Scotland - League One",
    "Scotland - League Two",
    "Scotland - Premiership",
    "Scotland - Scottish Cup",
    "Serbia - Kup Srbije",
    "Serbia - Prva Liga",
    "Serbia - Srspka Liga",
    "Serbia - Super Liga",
    "Singapore - Premier League",
    "Slovakia - 2. Liga",
    "Slovakia - 3. Liga",
    "Slovakia - Slovensky Pohar",
    "Slovakia - Superliga",
    "Slovenia - 2. SNL",
    "Slovenia - Cup",
    "Slovenia - PrvaLiga",
    "Slovenia - WFL",
    "South Africa - Premier League",
    "Spain - Copa del Rey",
    "Spain - Kings League",
    "Spain - La Liga",
    "Spain - La Liga 2",
    "Spain - Liga F",
    "Spain - Primera Federacion",
    "Spain - Supercopa",
    "Sweden - Allsvenskan",
    "Sweden - Damallsvenskan",
    "Sweden - Ettan",
    "Sweden - Superettan",
    "Sweden - Svenska Cupen",
    "Switzerland - Challenge League",
    "Switzerland - Cup",
    "Switzerland - Promotion League",
    "Switzerland - Super League",
    "Thailand - Thai League 1",
    "Turkey - 1. Lig",
    "Turkey - Cup",
    "Turkey - Super Lig",
    "UAE - League Cup",
    "UAE - Pro League",
    "UEFA - Champions League",
    "UEFA - Champions League Women",
    "UEFA - Europa Conference League",
    "UEFA - Europa League",
    "UEFA - European Championship",
    "UEFA - European Championship Qualifiers",
    "UEFA - European Championship Qualifiers U21",
    "UEFA - European Championship U21",
    "UEFA - European Championship Women",
    "UEFA - Nations League",
    "UEFA - Nations League Women",
    "UEFA - Super Cup",
    "USA - MLS Next Pro",
    "USA - Major League Soccer",
    "USA - NISA",
    "USA - NPSL",
    "USA - NWSL",
    "USA - Open Cup",
    "USA - USL Championship",
    "USA - USL League One",
    "USA - USL League Two",
    "USA - USL W League",
    "Ukraine - Cup",
    "Ukraine - Druha Liha",
    "Ukraine - Persha Liha",
    "Ukraine - Premier League",
    "Uruguay - Primera Division",
    "Uruguay - Segunda Division",
    "Uzbekistan - Cup",
    "Uzbekistan - Professional League",
    "Uzbekistan - Super League",
    "Venezuela - Copa Venezuela",
    "Venezuela - Primera Division",
    "Vietnam - V League 1",
    "Vietnam - V League 2",
    "WAFF - Championship",
    "WAFF - Championship Women",
    "Wales - Cymru Championship",
    "Wales - Cymru Premier",
    "Wales - Welsh Cup",
    "Zimbabwe - Premier League",
]

CACHE_FILE = "espn_leagues_catalog.json"
OUTPUT_DIR = "soccer_league_logos_custom"

# Explicit overrides: target name → exact ESPN league name (or None to skip/no match)
FORCE_MATCH = {
    # AFC
    "AFC - Champions League 2": "AFC Champions League Two",

    # CONMEBOL
    "CONMEBOL - Copa America": "Copa América",
    "CONMEBOL - Copa America Women": None,   # no logo in ESPN
    "CONMEBOL - Nations League": None,
    "CONMEBOL - Nations League Women": None,

    # CONCACAF
    "CONCACAF - Caribbean Cup": None,        # not in ESPN with logo
    "CONCACAF - Champions Cup Women": None,  # Concacaf W Championship has no logo

    # CAFA / COSAFA
    "CAFA - Nations Cup": None,

    # Germany
    "Germany - Bundesliga 2": "German 2. Bundesliga",
    "Germany - Bundesliga 3": None,
    "Germany - Frauen Bundesliga": None,     # no logo in ESPN

    # Austria
    "Austria - 2. Liga": None,               # not in ESPN catalog

    # Belgium
    "Belgium - Womens Super League": None,   # not in ESPN catalog

    # England
    "England - League 2": "English League Two",
    "England - FA Trophy": None,             # different from EFL Trophy

    # FIFA
    "FIFA - World Cup U20": "FIFA Under-20 World Cup",
    "FIFA - World Cup Women": "FIFA Women's World Cup",
    "FIFA - Intercontinental Cup": "FIFA Intercontinental Cup",

    # UEFA women / youth
    "UEFA - Champions League Women": "UEFA Women's Champions League",
    "UEFA - European Championship Qualifiers U21": "UEFA European Under-21 Championship",
    "UEFA - European Championship U21": "UEFA European Under-21 Championship",
    "UEFA - European Championship Women": "UEFA Women's European Championship",
    "UEFA - Nations League Women": None,     # UEFA Women's Nations League has no logo

    # USA
    "USA - Major League Soccer": "MLS",
    "USA - NWSL": "NWSL",
    "USA - Open Cup": "U.S. Open Cup",
    "USA - USL Championship": "USL Championship",
    "USA - USL League One": "USL League One",
    "USA - MLS Next Pro": None,
    "USA - NPSL": None,
    "USA - NISA": None,
    "USA - USL League Two": None,
    "USA - USL W League": None,

    # Ireland
    "Ireland - Premier League": "Irish Premier Division",
    "Ireland - Division 1": None,            # First Division not in ESPN catalog
    "Ireland - FAI Cup": None,

    # North America
    "North America - Leagues Cup": "Leagues Cup",

    # Argentina
    "Argentina - Primera Nacional": "Argentine Nacional B",

    # Brazil
    "Brazil - Serie D": None,                # no logo in ESPN

    # Chile
    "Chile - Primera B": None,               # Chilean Primera División ≠ Primera B

    # Cyprus
    "Cyprus - Third Division": None,

    # International
    "International - Kings Cup": None,       # different from International Champions Cup

    # Italy
    "Italy - Serie C": None,                 # no logo in ESPN

    # Japan
    "Japan - J2 League": None,               # only J.League has logo
    "Japan - J3 League": None,
    "Japan - League Cup": None,

    # Sweden
    "Sweden - Damallsvenskan": None,         # Allsvenskan is men's league

    # Portugal
    "Portugal - Liga 3": None,
    "Portugal - Segunda Liga": None,

    # Russia
    "Russia - First League": None,
    "Russia - Second League A": None,

    # Canada
    "Canada - Championship": None,           # ASEAN Championship is wrong
    "Canada - Premier League": None,         # Canadian Premier League not in ESPN
    "Canada - Soccer League": None,
}


def fetch_espn_leagues_catalog():
    """Fetch all ESPN soccer leagues with logos (cached)"""
    cache_path = Path(CACHE_FILE)

    if cache_path.exists():
        print("[Cache] Loading ESPN leagues catalog from cache...")
        with open(cache_path, encoding="utf-8") as f:
            catalog = json.load(f)
        print(f"[Cache] {len(catalog)} leagues loaded")
        return catalog

    print("[ESPN] Fetching full soccer leagues catalog (first time, please wait)...")
    catalog = []
    page = 1

    while True:
        list_url = f"http://sports.core.api.espn.com/v2/sports/soccer/leagues?limit=500&page={page}"
        r = requests.get(list_url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  [!] Failed page {page}: HTTP {r.status_code}")
            break

        data = r.json()
        items = data.get("items", [])
        total_pages = data.get("pageCount", 1)
        print(f"  Page {page}/{total_pages}: {len(items)} leagues — fetching details...")

        for i, item in enumerate(items, 1):
            ref = item.get("$ref", "")
            if not ref:
                continue

            league_id = ref.rstrip("/").split("/")[-1]

            r2 = requests.get(ref, headers=HEADERS, timeout=15)
            if r2.status_code == 200:
                d = r2.json()
                logos = d.get("logos", [])
                logo_url = logos[0].get("href") if logos else None

                catalog.append({
                    "id": league_id,
                    "slug": d.get("slug", ""),
                    "name": d.get("name", ""),
                    "displayName": d.get("displayName", ""),
                    "shortName": d.get("shortDisplayName", ""),
                    "abbreviation": d.get("abbreviation", ""),
                    "logo": logo_url,
                })
                print(f"    [{i}/{len(items)}] {d.get('name', league_id)}")
            time.sleep(0.15)

        if page >= total_pages:
            break
        page += 1

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"\n[Cache] Saved {len(catalog)} leagues to {CACHE_FILE}")
    return catalog


# Map target country names to keyword(s) that should appear in ESPN league name
COUNTRY_KEYWORDS = {
    "afc": ["afc"],
    "caf": ["caf", "africa", "african"],
    "cafa": ["cafa"],
    "cecafa": ["cecafa"],
    "concacaf": ["concacaf"],
    "conmebol": ["conmebol"],
    "cosafa": ["cosafa"],
    "waff": ["waff"],
    "asean": ["asean"],
    "fifa": ["fifa"],
    "uefa": ["uefa"],
    "kings league": ["kings"],
    "olympics": ["olympic"],
    "international": ["international", "friendly", "friendl", "champions cup"],
    "north america": ["leagues cup", "north america"],
    "albania": ["albanian", "albania"],
    "algeria": ["algerian", "algeria"],
    "andorra": ["andorran", "andorra"],
    "angola": ["angolan", "angola"],
    "argentina": ["argentina", "argentine", "argentinian"],
    "armenia": ["armenia", "armenian"],
    "australia": ["australia", "australian"],
    "austria": ["austria", "austrian"],
    "azerbaijan": ["azerbaijan", "azerbaijani"],
    "bahrain": ["bahrain", "bahraini"],
    "belarus": ["belarus", "belarusian"],
    "belgium": ["belgium", "belgian"],
    "bolivia": ["bolivia", "bolivian"],
    "bosnia": ["bosnia", "bosnian"],
    "brazil": ["brazil", "brazilian"],
    "bulgaria": ["bulgaria", "bulgarian"],
    "canada": ["canada", "canadian"],
    "chile": ["chile", "chilean"],
    "china": ["china", "chinese"],
    "colombia": ["colombia", "colombian"],
    "costa rica": ["costa rica", "costa rican"],
    "croatia": ["croatia", "croatian"],
    "cyprus": ["cyprus", "cypriot"],
    "czech republic": ["czech"],
    "denmark": ["denmark", "danish"],
    "ecuador": ["ecuador", "ecuadorian"],
    "egypt": ["egypt", "egyptian"],
    "el salvador": ["salvador", "salvadoran"],
    "england": ["england", "english"],
    "estonia": ["estonia", "estonian"],
    "ethiopia": ["ethiopia", "ethiopian"],
    "faroe islands": ["faroe", "faroese"],
    "finland": ["finland", "finnish"],
    "france": ["france", "french"],
    "georgia": ["georgia", "georgian"],
    "germany": ["germany", "german"],
    "gibraltar": ["gibraltar"],
    "greece": ["greece", "greek"],
    "guatemala": ["guatemala", "guatemalan"],
    "hong kong": ["hong kong"],
    "hungary": ["hungary", "hungarian"],
    "iceland": ["iceland", "icelandic"],
    "india": ["india", "indian"],
    "indonesia": ["indonesia", "indonesian"],
    "iraq": ["iraq", "iraqi"],
    "ireland": ["ireland", "irish"],
    "israel": ["israel", "israeli"],
    "italy": ["italy", "italian"],
    "jamaica": ["jamaica", "jamaican"],
    "japan": ["japan", "japanese"],
    "kazakhstan": ["kazakhstan", "kazakh"],
    "kenya": ["kenya", "kenyan"],
    "kosovo": ["kosovo", "kosovar"],
    "korea": ["korea", "korean"],
    "latvia": ["latvia", "latvian"],
    "lebanon": ["lebanon", "lebanese"],
    "liechtenstein": ["liechtenstein"],
    "lithuania": ["lithuania", "lithuanian"],
    "luxembourg": ["luxembourg"],
    "malaysia": ["malaysia", "malaysian"],
    "malta": ["malta", "maltese"],
    "mexico": ["mexico", "mexican"],
    "moldova": ["moldova", "moldovan"],
    "mongolia": ["mongolia", "mongolian"],
    "montenegro": ["montenegro"],
    "netherlands": ["netherlands", "dutch"],
    "new zealand": ["new zealand"],
    "north america": ["north america", "leagues cup"],
    "north macedonia": ["north macedonia", "macedonian"],
    "northern ireland": ["northern ireland"],
    "norway": ["norway", "norwegian"],
    "panama": ["panama", "panamanian"],
    "paraguay": ["paraguay", "paraguayan"],
    "peru": ["peru", "peruvian"],
    "poland": ["poland", "polish"],
    "portugal": ["portugal", "portuguese"],
    "qatar": ["qatar", "qatari"],
    "romania": ["romania", "romanian"],
    "russia": ["russia", "russian"],
    "san marino": ["san marino"],
    "saudi arabia": ["saudi"],
    "scotland": ["scotland", "scottish"],
    "serbia": ["serbia", "serbian"],
    "singapore": ["singapore", "singaporean"],
    "slovakia": ["slovakia", "slovak"],
    "slovenia": ["slovenia", "slovenian", "slovene"],
    "south africa": ["south africa", "south african"],
    "spain": ["spain", "spanish"],
    "sweden": ["sweden", "swedish"],
    "switzerland": ["switzerland", "swiss"],
    "thailand": ["thailand", "thai"],
    "turkey": ["turkey", "turkish"],
    "uae": ["uae", "emirati", "arabian gulf"],
    "ukraine": ["ukraine", "ukrainian"],
    "uruguay": ["uruguay", "uruguayan"],
    "uzbekistan": ["uzbekistan", "uzbek"],
    "venezuela": ["venezuela", "venezuelan"],
    "vietnam": ["vietnam", "vietnamese"],
    "wales": ["wales", "welsh"],
    "zimbabwe": ["zimbabwe", "zimbabwean"],
}


def normalize(s):
    """Normalize string for fuzzy matching"""
    s = s.lower()
    s = re.sub(r"['\-_/&.,()]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def country_is_compatible(target_country, espn_name):
    """Check if the target country is compatible with the ESPN league name."""
    target_lower = target_country.lower().strip()
    espn_lower = espn_name.lower()

    # Look up known keywords for this country
    for key, keywords in COUNTRY_KEYWORDS.items():
        if key in target_lower or target_lower in key:
            return any(kw in espn_lower for kw in keywords)

    # Fallback: check if any word from target country (3+ chars) appears in espn name
    words = [w for w in target_lower.split() if len(w) >= 3]
    return any(w in espn_lower for w in words)


def score_match(target, espn_name):
    """Score how well espn_name matches target, with strict country filtering."""
    # Parse "Country - Competition" format
    t_parts = target.split(" - ", 1)
    has_country = len(t_parts) == 2
    t_country = t_parts[0].strip() if has_country else ""
    t_comp = t_parts[1].strip() if has_country else target

    # STRICT: if target has "Country - " format, ESPN name must match country
    if has_country and t_country.lower() not in ("international", "olympics"):
        if not country_is_compatible(t_country, espn_name):
            return 0.0  # Hard reject — wrong country

    t_norm = normalize(target)
    e_norm = normalize(espn_name)

    if t_norm == e_norm:
        return 1.0

    score = SequenceMatcher(None, t_norm, e_norm).ratio()

    # Boost: competition keywords overlap
    comp_words = [w for w in normalize(t_comp).split() if len(w) > 3]
    if comp_words:
        hits = sum(1 for w in comp_words if w in e_norm)
        score = min(1.0, score + 0.04 * hits)

    return score


def find_best_match(target, catalog, threshold=0.72):
    """Find best matching ESPN league for target name, with force-match overrides."""
    # Check explicit overrides first
    if target in FORCE_MATCH:
        espn_name = FORCE_MATCH[target]
        if espn_name is None:
            return None, 0.0  # Force skip — known no match
        # Find the exact ESPN league in catalog
        for league in catalog:
            for field in ["name", "displayName", "shortName"]:
                if league.get(field, "") == espn_name:
                    return league, 1.0
        return None, 0.0  # Force match not found in catalog

    # Regular fuzzy matching
    best_match = None
    best_score = 0

    for league in catalog:
        for field in ["name", "displayName", "shortName"]:
            espn_name = league.get(field, "")
            if not espn_name:
                continue
            s = score_match(target, espn_name)
            if s > best_score:
                best_score = s
                best_match = league

    if best_score >= threshold:
        return best_match, best_score
    return None, best_score


def download_image(url, filepath):
    """Download image to filepath"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200 and len(r.content) > 200:
            with open(filepath, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DOWNLOADING SOCCER LEAGUE LOGOS — Custom List (ESPN)")
    print("=" * 70)

    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(exist_ok=True)

    # Step 1: Build ESPN catalog
    catalog = fetch_espn_leagues_catalog()
    print(f"\n[INFO] Catalog ready: {len(catalog)} ESPN leagues")
    print(f"[INFO] Target leagues: {len(LEAGUES_TO_FIND)}\n")
    print("=" * 70)

    downloaded = 0
    not_found = []
    low_confidence = []
    results = []

    for target_name in LEAGUES_TO_FIND:
        match, score = find_best_match(target_name, catalog)

        # File saved with EXACT target name
        safe_filename = target_name.replace("/", "-") + ".png"
        filepath = output_dir / safe_filename

        if match and match.get("logo"):
            logo_url = match["logo"]
            if download_image(logo_url, filepath):
                status = "OK " if score >= 0.85 else "OK?"
                print(f"[{status}] {target_name}")
                print(f"      ESPN: {match['name']} (score: {score:.2f})")
                downloaded += 1
                results.append({
                    "target": target_name,
                    "espn_name": match["name"],
                    "espn_slug": match["slug"],
                    "score": round(score, 3),
                    "logo": logo_url,
                    "file": safe_filename,
                })
                continue
            else:
                print(f"[DL!] {target_name} — download failed (ESPN: {match['name']})")
                not_found.append(target_name)
        else:
            if match:
                print(f"[---] {target_name}")
                print(f"      Best ESPN: {match['name']} (score: {score:.2f}) — no logo / below threshold")
            else:
                print(f"[---] {target_name} — no match found")
            not_found.append(target_name)

    # Summary
    print("\n" + "=" * 70)
    print(f"Downloaded : {downloaded}/{len(LEAGUES_TO_FIND)}")
    print(f"Not found  : {len(not_found)}")

    if not_found:
        print("\nNot found list:")
        for n in not_found:
            print(f"  - {n}")

    with open("custom_league_logos_results.json", "w", encoding="utf-8") as f:
        json.dump({"downloaded": results, "not_found": not_found}, f, indent=2, ensure_ascii=False)

    print(f"\n[Done] Logos saved in: {OUTPUT_DIR}/")
    print(f"[Done] Results log  : custom_league_logos_results.json")
    print("=" * 70)
