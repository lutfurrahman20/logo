import requests
import json
import re

url = "https://www.espn.com/soccer/team/squad/_/id/132/bayern-munich"
response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

scripts = response.text

match = re.search(r"window\[.__espnfitt__.\]\s*=\s*(\{.+?\});", scripts, re.DOTALL)
if match:
    data = json.loads(match.group(1))
    squad = data["page"]["content"]["squad"]
    groups = squad.get("groups", [])
    
    for group_idx, group in enumerate(groups):
        print(f"\nGroup {group_idx}: {group.get('name', 'Unknown')}")
        athletes = group.get("athletes", [])
        print(f"  Athletes: {len(athletes)}")
        
        if athletes:
            first = athletes[0]
            print(f"  First athlete type: {type(first)}")
            if isinstance(first, dict):
                print(f"  Keys: {list(first.keys())}")
                print(f"  Full data: {json.dumps(first, indent=2)}")
            elif isinstance(first, list):
                print(f"  Is list with {len(first)} items")
                if first:
                    print(f"  First item type: {type(first[0])}")
                    print(f"  First item: {first[0]}")
