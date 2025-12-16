import requests
import json

# --- CONFIGURACIÓN PARA API-FOOTBALL (DIRECTO) ---
# Fíjate que la URL cambió, ya no dice "rapidapi"
url = "https://v3.football.api-sports.io/fixtures"

headers = {
    'x-apisports-key': '8bfe23f584f1867b8ac0841f70d12009'
}

# Vamos a pedir los partidos de la Final del Mundo 2022 para asegurar que haya datos
# League 1 = Mundial. Season 2022.
params = {
    'date': '2025-12-14',
}

print("📡 Conectando directamente a API-Sports...")

try:
    response = requests.get(url, headers=headers, params=params)
    
    # Verificamos si la respuesta es correcta (Código 200)
    if response.status_code == 200:
        data = response.json()
        
        # Verificar si hay errores en el cuerpo de la respuesta (ej: clave inválida)
        if data.get('errors'):
            print("❌ Error reportado por la API:")
            print(data['errors'])
        else:
            partidos = data['response']
            print(f"✅ ¡Conexión Exitosa! Se encontraron {len(partidos)} partidos.")
            
            for match in partidos:
                local = match['teams']['home']['name']
                visitante = match['teams']['away']['name']
                goles_local = match['goals']['home']
                goles_visitante = match['goals']['away']
                estado = match['fixture']['status']['long']
                
                print(f"--------------------------------")
                print(f"🏆 {match['league']['name']} - {match['league']['round']}")
                print(f"⚽ {local} {goles_local} - {goles_visitante} {visitante}")
                print(f"📊 Estado: {estado}")

    else:
        print(f"❌ Error HTTP {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Error de conexión: {e}")