from django.core.management.base import BaseCommand
from core.models import Match, Team
import requests
from django.utils import timezone

class Command(BaseCommand):
    help = 'Consulta la API de fútbol y actualiza los resultados en la base de datos'

    def handle(self, *args, **kwargs):
        self.stdout.write("📡 Conectando a la API...")

        # --- TU CONFIGURACIÓN (La que funcionó) ---
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            'x-apisports-key': '8bfe23f584f1867b8ac0841f70d12009'
        }
        # Usamos la fecha que te dio resultados (el 14 o 15 de dic)
        params = {
            'date': '2025-12-17' 
        }

        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            self.stdout.write(self.style.ERROR('❌ Error de conexión con la API'))
            return

        data = response.json()
        partidos_api = data['response']
        
        count_actualizados = 0

        for item in partidos_api:
            # 1. Extraemos datos de la API
            nombre_local_api = item['teams']['home']['name']
            nombre_visitante_api = item['teams']['away']['name']
            goles_local = item['goals']['home']
            goles_visitante = item['goals']['away']
            estado = item['fixture']['status']['short'] # FT, NS, etc.
            # --- NUEVO: ESTA LÍNEA TE DIRÁ QUÉ ESTÁ VIENDO ---
            self.stdout.write(f"👀 La API ve: {nombre_local_api} vs {nombre_visitante_api}")
            # -------------------------------------------------

            # Solo nos interesa si el partido ya tiene goles
            if goles_local is None or goles_visitante is None:
                continue

            # 2. Buscamos el partido en NUESTRA Base de Datos
            # Intentamos buscar un Match donde los equipos coincidan por nombre
            # (Usamos __icontains para que ignore mayúsculas/minúsculas)
            partido_db = Match.objects.filter(
                home_team__name__icontains=nombre_local_api,
                away_team__name__icontains=nombre_visitante_api
            ).first()

            if partido_db:
                # 3. Si existe, actualizamos
                partido_db.home_goals = goles_local
                partido_db.away_goals = goles_visitante
                
                # Si el partido terminó (FT = Full Time), podríamos marcarlo como finalizado
                # (Opcional, depende de tu modelo)
                
                partido_db.save()

                
                # --- NUEVO: ACTUALIZAMOS LOS ESCUDOS ---
                # Extraemos las URLs del JSON de la API
                url_logo_local = item['teams']['home']['logo']
                url_logo_visitante = item['teams']['away']['logo']

                # Guardamos en el equipo Local
                # Solo guardamos si no tiene logo o si es distinto (para no guardar a cada rato)
                if partido_db.home_team.logo != url_logo_local:
                    partido_db.home_team.logo = url_logo_local
                    partido_db.home_team.save()
                    self.stdout.write(f"   --> Logo actualizado para {nombre_local_api}")

                # Guardamos en el equipo Visitante
                if partido_db.away_team.logo != url_logo_visitante:
                    partido_db.away_team.logo = url_logo_visitante
                    partido_db.away_team.save()
                    self.stdout.write(f"   --> Logo actualizado para {nombre_visitante_api}")
                # ---------------------------------------
                
                self.stdout.write(self.style.SUCCESS(f"✅ Actualizado: {nombre_local_api} {goles_local}-{goles_visitante} {nombre_visitante_api}"))
                count_actualizados += 1
            else:
                # --- AGREGA ESTO ---
                self.stdout.write(self.style.WARNING(f"⚠️  No encontré coincidencia para: {nombre_local_api} vs {nombre_visitante_api}"))
                self.stdout.write(f"    (Revisá que en tu Admin los equipos se llamen parecido)")

        self.stdout.write(self.style.SUCCESS(f"✨ Proceso terminado. Partidos actualizados: {count_actualizados}"))