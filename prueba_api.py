import requests
import json

# 1. Configuración
url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

# Queremos ver los partidos de HOY
# Ojo: Si hoy no hay partidos interesantes, la lista saldrá vacía.
# Puedes cambiar la fecha a un día que sepas que hubo fútbol (ej: '2022-12-18' la final del mundo)
querystring = {"date": "2023-11-21"} 

headers = {
	"X-RapidAPI-Key": "57869ce1a1msh82e5d398f20ccb7p11a477jsnb1a7483a2731",
	"X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

print("📡 Consultando a la API...")

# 2. Hacemos el pedido (Request)
response = requests.get(url, headers=headers, params=querystring)

# 3. Analizamos la respuesta
if response.status_code == 200:
    data = response.json()
    cantidad = data['results']
    print(f"✅ ¡Éxito! Se encontraron {cantidad} partidos.")
    
    # Vamos a mostrar solo los primeros 3 para no llenar la pantalla
    # La API devuelve una lista dentro de 'response'
    for match in data['response'][:3]:
        local = match['teams']['home']['name']
        visitante = match['teams']['away']['name']
        goles_local = match['goals']['home']
        goles_visitante = match['goals']['away']
        estado = match['fixture']['status']['short'] # FT = Finalizado, NS = No Empezado
        
        print(f"--------------------------------")
        print(f"⚽ {local} vs {visitante}")
        print(f"📊 Estado: {estado}")
        print(f"🥅 Resultado: {goles_local} - {goles_visitante}")
        
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)