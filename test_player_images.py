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
    
    all_players = []
    for group in groups:
        athletes = group.get("athletes", [])
        for athlete in athletes:
            player_name = athlete.get("name")
            player_href = athlete.get("href")
            
            # Extract player ID from href
            if player_href:
                id_match = re.search(r'/id/(\d+)/', player_href)
                if id_match:
                    player_id = id_match.group(1)
                    
                    # Construct headshot URL
                    headshot_url = f"https://a.espncdn.com/i/headshots/soccer/players/full/{player_id}.png"
                    
                    all_players.append({
                        "name": player_name,
                        "id": player_id,
                        "url": headshot_url
                    })
    
    print(f"Total players: {len(all_players)}")
    print("\nFirst 5 players:")
    for player in all_players[:5]:
        print(f"  {player['name']} (ID: {player['id']})")
        print(f"    URL: {player['url']}")
        
        # Test if image exists
        try:
            r = requests.head(player['url'], timeout=5)
            print(f"    Status: {r.status_code}")
        except:
            print(f"    Status: Error")
