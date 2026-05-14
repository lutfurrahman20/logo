import requests
import time
import re
from pathlib import Path

SAVE_DIR = Path(r"f:\logo\ucl_logos")

# Only leagues that actually return data in ESPN's API
LEAGUE_SLUGS = [
    "uefa.champions", "uefa.europa",
    "eng.1", "esp.1", "ita.1", "ger.1", "fra.1", "ger.2",
    "ned.1", "por.1", "bel.1",
    "sco.1", "nir.1",
    "tur.1", "aut.1", "sui.1",
    "gre.1", "rou.1", "cyp.1", "mlt.1",
    "den.1", "nor.1", "swe.1",
    "isr.1", "arg.1",
]


def sanitize_filename(name: str) -> str:
    """Replace characters invalid in Windows filenames."""
    return re.sub(r'[\\/:*?"<>|]', '-', name)


# save_name -> ESPN displayName
TEAM_MAP = {
    "1. FC Union Berlin":                       "Union Berlin",
    "AC Milan":                                  "AC Milan",
    "AC Sparta Praha":                           "Sparta Prague",
    "AEK Athens FC":                             "AEK Athens",
    "AFC Ajax":                                  "Ajax Amsterdam",
    "APOEL FC":                                  "Apoel Nicosia",
    "AS Monaco FC":                              "AS Monaco",
    "Aris FC Limassol":                          "Aris Limassol",
    "Arsenal FC":                                "Arsenal",
    "Arsenal de Sarandí":                        "Arsenal de Sarandí",
    "Aston Villa FC":                            "Aston Villa",
    "Atalanta Bergamasca Calcio":                "Atalanta",
    "Athletic Club Bilbao":                      "Athletic Club",
    "BK Häcken":                                 "BK Häcken",
    "BSC Young Boys":                            "Young Boys",
    "BV Borussia 09 Dortmund":                   "Borussia Dortmund",
    "Bayer 04 Leverkusen":                       "Bayer Leverkusen",
    "Bologna FC 1909":                           "Bologna",
    "Breidablik UBK":                            "Breidablik",
    "CS Petrocub Hînceşti":                      "Petrocub",
    "Celtic FC":                                 "Celtic",
    "Chelsea FC":                                "Chelsea",
    "Club Atlético de Madrid":                   "Atlético Madrid",
    "Club Brugge KV":                            "Club Brugge",
    "Eintracht Frankfurt":                       "Eintracht Frankfurt",
    "FC BATE Borisov":                           "BATE Borisov",
    "FC Barcelona":                              "Barcelona",
    "FC Basel 1893":                             "FC Basel",
    "FC Bayern München":                         "Bayern Munich",
    "FC Differdange 03":                         "Differdange",
    "FC Dinamo Batumi":                          "Dinamo Batumi",
    "FC Dinamo Minsk":                           "Dinamo Minsk",
    "FC Dinamo Tbilisi":                         "Dinamo Tbilisi",
    "FC Dynamo Kyiv":                            "Dynamo Kyiv",
    "FC Flora Tallinn":                          "FC Flora Tallin",
    "FC Iberia 1999":                            "Iberia 1999",
    "FC Internazionale Milano":                  "Internazionale",
    "FC København":                              "F.C. København",
    "FC Lugano":                                 "FC Lugano",
    "FC Midtjylland":                            "FC Midtjylland",
    "FC Milsami Orhei":                          "Milsami Orhei",
    "FC Noah":                                   "Noah",
    "FC Porto":                                  "FC Porto",
    "FC Salzburg":                               "RB Salzburg",
    "FC Shakhtar Donetsk":                       "Shakhtar Donetsk",
    "FC Struga Trim-Lum":                        "Struga",
    "FC Swift Hesperange":                       "Swift Hesperange",
    "FC Twente":                                 "FC Twente",
    "FC Urartu":                                 "Urartu",
    "FC Viktoria Plzeň":                         "Viktoria Plzen",
    "FCV Farul Constanţa":                       "FC Farul Constanta",
    "FK Astana":                                 "FC Astana",
    "FK Bodø / Glimt":                           "Bodo/Glimt",
    "FK Borac Banja Luka":                       "FK Borac Banja Luka",
    "FK Budućnost Podgorica":                    "Budućnost Podgorica",
    "FK Crvena zvezda Beograd":                  "Red Star Belgrade",
    "FK Dečić":                                  "Dečić",
    "FK Ordabasy Shymkent":                      "Ordabasy",
    "FK Panevėžys":                              "Panevėžys",
    "FK Partizan Beograd":                       "Partizan Belgrade",
    "FK Rīgas Futbola skola":                    "Rīgas FS",
    "FK Sheriff Tiraspol":                       "Sheriff Tiraspol",
    "FK TSC Bačka Topola":                       "TSC Backa Topola",
    "FK Valmiera":                               "Valmiera",
    "FK Žalgiris Vilnius":                       "Zalgiris Vilnius",
    "Fenerbahçe Spor Kulübü":                    "Fenerbahce",
    "Ferencvárosi TC":                           "Ferencvaros",
    "Feyenoord Rotterdam":                       "Feyenoord Rotterdam",
    "GNK Dinamo Zagreb":                         "Dinamo Zagreb",
    "Galatasaray Spor Kulübü":                   "Galatasaray",
    "Girona FC":                                 "Girona",
    "HNK Rijeka":                                "Rijeka",
    "Hamrun Spartans FC":                        "Hamrun Spartans",
    "Helsingin Jalkapalloklubi":                 "HJK Helsinki",
    "HŠK Zrinjski Mostar":                       "Zrinjski",
    "Inter Club d'Escaldes":                     "Inter Club d'Escaldes",
    "Juventus FC":                               "Juventus",
    "KF Ballkani":                               "Ballkani",
    "KF Drita":                                  "Drita",
    "KF Partizani Tirana":                       "Partizani",
    "KF Shkendija":                              "Shkëndija",
    "KKS Lech Poznań":                           "Lech Poznan",
    "KRC Genk":                                  "Racing Genk",
    "KS Egnatia Rrogozhinë":                     "Egnatia",
    "KS Raków Częstochowa":                      "Rakow Czestochowa",
    "Kairat Almaty":                             "Kairat Almaty",
    "Kuopion Palloseura":                        "KuPS",
    "KÍ Klaksvík":                               "KÍ Klaksvík",
    "Larne FC":                                  "Larne",
    "Lille OSC":                                 "Lille",
    "Lincoln Red Imps FC":                       "Lincoln Red Imps",
    "Linfield FC":                               "Linfield",
    "Liverpool FC":                              "Liverpool",
    "M-Perruquers Atlètic Club d'Escaldes":      "Atlètic Club d'Escaldes",
    "Maccabi Haifa FC":                          "Maccabi Haifa",
    "Maccabi Tel Aviv FC":                       "Maccabi Tel-Aviv",
    "Malmö FF":                                  "Malmö FF",
    "Manchester City FC":                        "Manchester City",
    "Manchester United FC":                      "Manchester United",
    "Molde FK":                                  "Molde",
}

# Direct ID overrides for confirmed IDs (save_name -> id)
# Priority over TEAM_MAP displayName lookups
DIRECT_IDS = {
    # Confirmed via UCL/Europa/national league APIs
    "1. FC Union Berlin":           598,
    "AC Milan":                     103,
    "AEK Athens FC":                887,
    "AFC Ajax":                     139,
    "APOEL FC":                     2497,
    "AS Monaco FC":                 174,
    "Aris FC Limassol":             21530,
    "Arsenal FC":                   359,
    "Aston Villa FC":               362,
    "Atalanta Bergamasca Calcio":   105,
    "Athletic Club Bilbao":         93,
    "BK Häcken":                    7834,
    "BSC Young Boys":               2722,
    "BV Borussia 09 Dortmund":      124,
    "Bayer 04 Leverkusen":          131,
    "Bologna FC 1909":              107,
    "Celtic FC":                    256,
    "Chelsea FC":                   363,
    "Club Atlético de Madrid":      1068,
    "Club Brugge KV":               570,
    "Eintracht Frankfurt":          125,
    "FC BATE Borisov":              497,
    "FC Barcelona":                 83,
    "FC Basel 1893":                989,
    "FC Bayern München":            132,
    "FC Dinamo Tbilisi":            498,
    "FC Flora Tallinn":             563,
    "FC Internazionale Milano":     110,
    "FC København":                 909,
    "FC Lugano":                    7672,
    "FC Midtjylland":               572,
    "FC Porto":                     437,
    "FC Salzburg":                  2790,
    "FC Shakhtar Donetsk":          493,
    "FC Twente":                    152,
    "FC Viktoria Plzeň":            11706,
    "FCV Farul Constanţa":          6731,
    "FK Bodø / Glimt":              2980,
    "FK Crvena zvezda Beograd":     2290,
    "FK Partizan Beograd":          541,
    "FK Sheriff Tiraspol":          614,
    "FK Žalgiris Vilnius":          523,
    "Fenerbahçe Spor Kulübü":       436,
    "Ferencvárosi TC":              622,
    "Feyenoord Rotterdam":          142,
    "GNK Dinamo Zagreb":            597,
    "Galatasaray Spor Kulübü":      432,
    "Girona FC":                    9812,
    "Hamrun Spartans FC":           7858,
    "Helsingin Jalkapalloklubi":    502,
    "Juventus FC":                  111,
    "Kairat Almaty":                2528,
    "KRC Genk":                     938,
    "Larne FC":                     20039,
    "Lille OSC":                    166,
    "Linfield FC":                  2555,
    "Liverpool FC":                 364,
    "Maccabi Haifa FC":             611,
    "Maccabi Tel Aviv FC":          524,
    "Malmö FF":                     2720,
    "Manchester City FC":           382,
    "Manchester United FC":         360,
    "Molde FK":                     2715,
    # Newly found via ESPN search API
    "AC Sparta Praha":              433,
    "Breidablik UBK":               8250,
    "CS Petrocub Hînceşti":         19250,
    "FC Differdange 03":            7759,
    "FC Dinamo Batumi":             12344,
    "FC Dinamo Minsk":              2539,
    "FC Dynamo Kyiv":               440,
    "FC Milsami Orhei":             11440,
    "FC Noah":                      20712,
    "FC Struga Trim-Lum":           20999,
    "FC Swift Hesperange":          21002,
    "FC Urartu":                    2719,
    "FK Astana":                    12124,
    "FK Borac Banja Luka":          20710,
    "FK Budućnost Podgorica":       7822,
    "FK Dečić":                     21001,
    "FK Ordabasy Shymkent":         7962,
    "FK Panevėžys":                 21004,
    "FK Rīgas Futbola skola":       12030,
    "FK TSC Bačka Topola":          20713,
    "FK Valmiera":                  20719,
    "HNK Rijeka":                   2988,
    "HŠK Zrinjski Mostar":          5239,
    "Inter Club d'Escaldes":        20703,
    "KF Ballkani":                  21526,
    "KF Drita":                     19243,
    "KF Partizani Tirana":          2551,
    "KF Shkendija":                 8151,
    "KKS Lech Poznań":              2990,
    "KS Egnatia Rrogozhinë":        21943,
    "KS Raków Częstochowa":         21005,
    "Kuopion Palloseura":           8169,
    "KÍ Klaksvík":                  2547,
    "Lincoln Red Imps FC":          17856,
    "M-Perruquers Atlètic Club d'Escaldes": 21528,
    "Arsenal de Sarandí":           2635,
}


def fetch_league_teams(league_slug):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/teams?limit=200"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        teams = data["sports"][0]["leagues"][0]["teams"]
        return {t["team"]["displayName"]: t["team"]["id"] for t in teams}
    except Exception:
        return {}


def download_logo(team_id, save_path):
    url = f"https://a.espncdn.com/i/teamlogos/soccer/500/{team_id}.png"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    save_path.write_bytes(resp.content)


def main():
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    print("Building supplemental team ID database from ESPN league APIs...")
    all_teams = {}
    for slug in LEAGUE_SLUGS:
        result = fetch_league_teams(slug)
        if result:
            all_teams.update(result)
            print(f"  {slug}: {len(result)} teams")
        time.sleep(0.1)
    print(f"Total unique teams from leagues: {len(all_teams)}\n")

    saved = failed = 0
    not_found = []

    for save_name, espn_name in TEAM_MAP.items():
        # DIRECT_IDS takes priority (manually verified IDs)
        team_id = DIRECT_IDS.get(save_name)
        if team_id is None:
            team_id = all_teams.get(espn_name)
        if team_id is None:
            not_found.append((save_name, espn_name))
            failed += 1
            continue

        # Sanitize filename — replace characters invalid on Windows (e.g. "/" in Bodø/Glimt)
        safe_name = sanitize_filename(save_name)
        dest = SAVE_DIR / f"{safe_name}.png"
        try:
            download_logo(team_id, dest)
            label = save_name if safe_name == save_name else f"{save_name}  →  {safe_name}.png"
            print(f"Saved:  {label}  (id={team_id})")
            saved += 1
        except Exception as e:
            print(f"FAILED: {save_name} — {e}")
            failed += 1
        time.sleep(0.08)

    print(f"\nDone: {saved} saved, {failed} failed/not found")
    if not_found:
        print("\nNOT FOUND (ESPN displayName tried):")
        for sn, en in not_found:
            print(f"  {sn!r}  (tried: {en!r})")
    print(f"\nLogos saved to: {SAVE_DIR}")


if __name__ == "__main__":
    main()
