import requests, re

h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

r = requests.get('https://www.afcb.co.uk/_nuxt/BkkXEZch.js', headers=h, timeout=30)
print(f'JS bundle: {r.status_code} {len(r.text)}')

# Find auth-related code
auth_patterns = re.findall(r'(?:Authorization|Bearer|x-api-key|apiKey|clientId)[^,;]{0,100}', r.text, re.I)
for p in auth_patterns[:10]:
    print(f'Auth: {p[:100]}')
    
# Find guest auth endpoint
guest_auth = re.findall(r'"https?://[^\s"\']{10,}(?:auth|token|guest)[^\s"\']{0,50}"', r.text, re.I)
print('Auth URLs:', guest_auth[:5])

# Look for players API
player_urls = re.findall(r'"https?://[^\s"\']*(?:player|squad|team)[^\s"\']{0,50}"', r.text, re.I)
seen = []
for u in player_urls:
    if u not in seen:
        seen.append(u)
print('Player URLs:', seen[:10])
