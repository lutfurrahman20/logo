import requests
import json

# Try the ESPN API
api_url = "https://site.api.espn.com/apis/site/v2/sports/soccer/ger.1/teams/132/roster"

try:
    response = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    data = response.json()
    
    if 'athletes' in data:
        athletes = data['athletes']
        print(f"Number of athletes: {len(athletes)}")
        
        # Check all athletes for image-related fields
        image_fields = set()
        for athlete in athletes:
            # Recursively search for image/photo/headshot keywords
            def find_image_fields(obj, prefix=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_prefix = f"{prefix}.{key}" if prefix else key
                        if any(word in key.lower() for word in ['image', 'photo', 'headshot', 'picture', 'avatar', 'img']):
                            image_fields.add(new_prefix)
                        find_image_fields(value, new_prefix)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        find_image_fields(item, f"{prefix}[{i}]")
            
            find_image_fields(athlete)
        
        if image_fields:
            print("\nImage-related fields found:")
            for field in sorted(image_fields):
                print(f"  {field}")
            
            # Show example value
            first = athletes[0]
            print("\nExample values from first athlete:")
            for field in sorted(image_fields):
                parts = field.split('.')
                value = first
                for part in parts:
                    if '[' in part:
                        key, idx = part.split('[')
                        idx = int(idx.rstrip(']'))
                        value = value.get(key, [])[idx] if isinstance(value, dict) else value[idx]
                    else:
                        value = value.get(part) if isinstance(value, dict) else None
                        if value is None:
                            break
                print(f"  {field}: {value}")
        else:
            print("\nNo image-related fields found in the API response!")
            print("\nThis means ESPN doesn't provide player images for soccer teams via their API.")
            print("You may need to use alternative sources like:")
            print("  - Transfermarkt")
            print("  - Wikipedia")
            print("  - Official team websites")
            print("  - Other soccer data providers")
                
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
