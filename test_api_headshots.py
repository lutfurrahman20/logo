import requests
import json

# Try the ESPN API
api_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/teams/132/roster"

try:
    response = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    data = response.json()
    
    print("API Response keys:", list(data.keys()))
    
    if 'athletes' in data:
        athletes = data['athletes']
        print(f"\nNumber of athletes: {len(athletes)}")
        
        if athletes:
            first = athletes[0]
            print("\nFirst athlete keys:", list(first.keys()))
            print("\nFirst athlete data:")
            print(json.dumps(first, indent=2))
            
            # Check if headshot exists
            if 'headshot' in first:
                print("\nHeadshot data found!")
                print(json.dumps(first['headshot'], indent=2))
                
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
