import requests

api_token = '1988cfde850245faaaceaf5d9ff33ada' # Tu token
uri = 'https://api.football-data.org/v4/competitions'
headers = { 'X-Auth-Token': api_token }

response = requests.get(uri, headers=headers)
competitions = response.json().get('competitions', [])

print(f"{'ID':<6} | {'NOMBRE':<30} | {'PLAN'}")
print("-" * 50)

for c in competitions:
    # Solo mostramos las del plan gratuito (TIER_ONE) para que no te den error
    if c.get('plan') == 'TIER_ONE': 
        print(f"{c['id']:<6} | {c['name']:<30} | {c['plan']}")