import json
from pathlib import Path

with open("cricket_league_logos_results.json", encoding="utf-8") as f:
    data = json.load(f)

# Add ICC T20 WC Qualifiers Women (was downloaded manually)
entry = {
    "name": "ICC - T20 World Cup Qualifiers Women",
    "source": "wikimedia (2026 ICC Women's T20 World Cup logo text only.png)",
    "url": "https://upload.wikimedia.org/wikipedia/commons/4/4f/2026_ICC_Women%27s_T20_World_Cup_logo_text_only.png",
    "file": "cricket_league_logos/ICC_T20_World_Cup_Qualifiers_Women.png",
}
results = data.get("results", [])
if not any(r["name"] == entry["name"] for r in results):
    results.append(entry)

not_found = [n for n in data.get("not_found", []) if n != "ICC - T20 World Cup Qualifiers Women"]

# Count actual files on disk
total = len(list(Path("cricket_league_logos").glob("*.*")))

data["downloaded"] = total
data["not_found_count"] = len(not_found)
data["results"] = sorted(results, key=lambda x: x["name"])
data["not_found"] = sorted(not_found)

with open("cricket_league_logos_results.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Updated: {total} downloaded, {len(not_found)} not found")
print("\nDownloaded logos:")
for r in data["results"]:
    print(f"  ✅ {r['name']}  [{r['source']}]")
print(f"\nNot found ({len(not_found)}):")
for n in not_found:
    print(f"  ⚠️  {n}")
