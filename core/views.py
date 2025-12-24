from django.shortcuts import render, redirect, get_object_or_404
from .models import Match, Prediction, Team, Tournament, TournamentMember, Competition, Standing
from .forms import PredictionForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone # <--- IMPORTANTE
from django.core.management import call_command
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
import io
from .forms import TournamentForm
from django.db.models import Q
from django.contrib import messages
import requests
from datetime import timedelta
from itertools import groupby
from operator import attrgetter
from django.db.models import Sum, Count, Avg
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from .forms import EditarPerfilForm
from datetime import datetime, timedelta
# En core/views.py

# En core/views.py

@login_required
def home(request):
    # 1. RECUPERAR MEMORIA (Solo para pintar el menú)
    comp_id = request.session.get('competencia_id')
    competencia_activa = None
    if comp_id:
        competencia_activa = Competition.objects.filter(id=comp_id).first()

    # 2. LÓGICA DE FECHAS (CORREGIDA CON LOCALDATE) 🕒
    fecha_str = request.GET.get('fecha')
    
    # ¡ESTA ES LA CLAVE! Usamos la fecha local de Argentina, no la UTC del servidor
    hoy = timezone.localdate() 

    if fecha_str:
        try:
            fecha_seleccionada = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_seleccionada = hoy
    else:
        fecha_seleccionada = hoy

    # Calculamos día anterior y siguiente para las flechas
    dia_anterior = fecha_seleccionada - timedelta(days=1)
    dia_siguiente = fecha_seleccionada + timedelta(days=1)

    # Definimos la ETIQUETA (El texto del medio)
    delta = (fecha_seleccionada - hoy).days
    
    if delta == 0:
        texto_fecha = "PARTIDOS DE HOY"
    elif delta == 1:
        texto_fecha = "MAÑANA"
    elif delta == -1:
        texto_fecha = "AYER"
    else:
        # Formato estilo 25/12
        texto_fecha = fecha_seleccionada.strftime("%d/%m")

    # 3. BUSCAR PARTIDOS (Solo del día seleccionado)
    partidos_dia = Match.objects.filter(
        date__date=fecha_seleccionada # Django convierte esto a tu zona horaria automáticamente
    ).select_related('competition', 'home_team', 'away_team').order_by('competition', 'date')

    # 4. EMPAQUETAR
    partidos_mostrar = []
    for partido in partidos_dia:
        prediccion = Prediction.objects.filter(user=request.user, match=partido).first()
        partidos_mostrar.append({
            'partido': partido,
            'prediccion': prediccion,
            'competition': partido.competition
        })

    return render(request, 'core/home.html', {
        'partidos_hoy': partidos_mostrar,
        'competencia_activa': competencia_activa,
        'texto_fecha': texto_fecha,
        'fecha_anterior': dia_anterior.strftime('%Y-%m-%d'),
        'fecha_siguiente': dia_siguiente.strftime('%Y-%m-%d'),
        'es_hoy': (fecha_seleccionada == hoy)
    })

@login_required # ¡Ojo! Solo usuarios logueados pueden predecir
def predecir_partido(request, match_id):
    partido = get_object_or_404(Match, id=match_id)
    
    # --- NUEVA REGLA: VALIDACIÓN DE HORARIO ---
    # Si la fecha del partido es menor a "ahora", ya empezó.
    if partido.date < timezone.now():
        # Opción A: Mostrar error feo
        # return HttpResponse("El partido ya empezó, tarde piaste.")
        
        # Opción B (Mejor): Redirigir al home y que se de cuenta solo
        return redirect('home')
    # ------------------------------------------

    prediccion_existente = Prediction.objects.filter(user=request.user, match=partido).first()

    if request.method == 'POST':
        # Si envió datos, cargamos el formulario con esos datos
        form = PredictionForm(request.POST, instance=prediccion_existente)
        if form.is_valid():
            # Guardamos pero sin enviar a la DB todavía (commit=False)
            prediccion = form.save(commit=False)
            # Asignamos los datos faltantes que no vienen en el form
            prediccion.user = request.user
            prediccion.match = partido
            prediccion.save() # ¡Ahora sí guardamos!
            # --- CAMBIO AQUÍ: REDIRECCIÓN INTELIGENTE ---
            # 1. Obtenemos el nombre de la ronda (Ej: "Fecha 16")
            ronda = partido.round_name
            
            # 2. Armamos la URL para que abra esa ronda y baje hasta el partido
            # El signo # hace que el navegador baje hasta el ID del partido
            return redirect(f"/?ronda={ronda}#group-{ronda}")
            # --------------------------------------------# Lo mandamos al inicio
    else:
        # Si solo está visitando la página, mostramos el form (vacío o con datos previos)
        form = PredictionForm(instance=prediccion_existente)

    return render(request, 'core/prediccion.html', {'form': form, 'partido': partido})
@login_required
def ranking(request, tournament_id=None):
    # 1. Si no hay ID, mandar a Mis Torneos
    if not tournament_id:
        messages.warning(request, "Debes seleccionar un torneo primero.")
        return redirect('mis_torneos')

    torneo = get_object_or_404(Tournament, id=tournament_id)
    
    # 2. Verificar si el usuario pertenece al torneo (Mirando la tabla intermedia explícitamente)
    soy_miembro = TournamentMember.objects.filter(
        user=request.user, 
        tournament=torneo,
        status='ACCEPTED' # Solo dejamos pasar si está Aceptado
    ).exists()

    if not soy_miembro:
        # Si no es miembro aceptado, lo rebotamos
        messages.error(request, "No tienes permiso para ver este torneo o tu solicitud sigue pendiente.")
        return redirect('mis_torneos')

    # 3. Armar la Tabla de Posiciones
    ranking_data = []
    
    # Traemos a todos los miembros aceptados, ordenados por puntos (Mayor a menor)
    miembros = TournamentMember.objects.filter(
        tournament=torneo, 
        status='ACCEPTED'
    ).select_related('user').order_by('-points')

    for i, miembro in enumerate(miembros, 1):
        ranking_data.append({
            'posicion': i,
            'usuario': miembro.user.username,
            'puntos': miembro.points,
            'es_el_usuario': (miembro.user == request.user)
        })

    return render(request, 'core/ranking.html', {
        'ranking_data': ranking_data,
        'titulo': f"🏆 {torneo.name}",
        'torneo': torneo
    })

    # 3. Ordenamos la lista de mayor a menor puntaje
    # lambda es una forma corta de decir: "ordena usando la clave 'puntos'"
    lista_ranking.sort(key=lambda x: x['puntos'], reverse=True)

    return render(request, 'core/ranking.html', {'ranking': lista_ranking})

@login_required
def actualizar_partidos_web(request):
    if not request.user.is_staff:
        messages.error(request, "Solo el administrador puede actualizar partidos.")
        return redirect('home')

    # --- TU TOKEN REAL AQUÍ ---
    API_TOKEN = '1988cfde850245faaaceaf5d9ff33ada' 
    # --------------------------
    
    base_url = "https://api.football-data.org/v4/matches"
    headers = {'X-Auth-Token': API_TOKEN}
    
    # Rango de fechas
    hoy = timezone.now().date()
    ayer = hoy - timedelta(days=5)
    manana = hoy + timedelta(days=5)
    
    params = {
        'dateFrom': ayer.strftime('%Y-%m-%d'),
        'dateTo': manana.strftime('%Y-%m-%d')
    }

    reporte = [] 

    try:
        response = requests.get(base_url, headers=headers, params=params)
        data = response.json()
        
        if 'matches' in data:
            for item in data['matches']:
                local = item['homeTeam']['name']
                visitante = item['awayTeam']['name']
                goles_local = item['score']['fullTime']['home']
                goles_visitante = item['score']['fullTime']['away']
                estado = item['status']
                
                # Info para el reporte
                info_partido = {
                    'partido': f"{local} vs {visitante}",
                    'resultado': f"{goles_local} - {goles_visitante}" if goles_local is not None else "- vs -",
                    'estado': estado,
                    'accion': 'Ignorado (No existe en DB)'
                }

                # Buscar en DB
                partido_db = Match.objects.filter(
                    home_team_name_icontains=local,
                    away_team_name_icontains=visitante
                ).first()

                if partido_db:
                    info_partido['accion'] = '✅ Actualizado'
                    
                    # 1. ACTUALIZAR DATOS BÁSICOS
                    if goles_local is not None:
                        partido_db.home_goals = goles_local
                        partido_db.away_goals = goles_visitante
                    
                    partido_db.date = item['utcDate']
                    partido_db.status = estado # Guardamos el estado (FINISHED, TIMED, etc)
                    partido_db.save()

                    # 2. CALCULAR PUNTOS (🔥 CORRECCIÓN AQUÍ 🔥)
                    # Solo entramos a calcular si EFECTIVAMENTE hay goles cargados
                    if goles_local is not None and goles_visitante is not None:
                        
                        preds = Prediction.objects.filter(match=partido_db)
                        puntos_repartidos = 0
                        
                        # Calculamos ganador real (Ahora es seguro porque no son None)
                        winner_real = "H" if goles_local > goles_visitante else "A" if goles_visitante > goles_local else "D"
                        
                        for pred in preds:
                            pts = 0
                            # A. Acierto Exacto (3 pts)
                            if pred.predicted_home == goles_local and pred.predicted_away == goles_visitante:
                                pts = 3
                            else:
                                # B. Acierto de Tendencia (1 pt)
                                winner_pred = "H" if pred.predicted_home > pred.predicted_away else "A" if pred.predicted_away > pred.predicted_home else "D"
                                
                                if winner_real == winner_pred:
                                    pts = 1
                            
                            # Guardar solo si cambió el puntaje
                            if pred.points != pts:
                                pred.points = pts
                                pred.save()
                                puntos_repartidos += 1
                                
                        if puntos_repartidos > 0:
                            info_partido['accion'] += f" y Puntos Recalculados ({puntos_repartidos} preds)"

                reporte.append(info_partido)

            # 3. RECALCULAR PUNTAJES TOTALES DE LOS TORNEOS
            miembros = TournamentMember.objects.filter(status='ACCEPTED')
            for m in miembros:
                # Sumamos todos los puntos de las predicciones de este usuario
                total = Prediction.objects.filter(user=m.user).aggregate(Sum('points'))['points__sum'] or 0
                if m.points != total:
                    m.points = total
                    m.save()

        else:
            messages.warning(request, "La API respondió OK pero sin partidos.")

    except Exception as e:
        print(f"ERROR EN UPDATE: {e}") # Para ver en la consola negra
        messages.error(request, f"Error: {e}")
        return redirect('mis_torneos')

    return render(request, 'core/actualizar_resultados.html', {'reporte': reporte})
    
@login_required
def mis_torneos(request):
    # --- 1. LÓGICA DE COMPETENCIA (Tu código original) ---
    comp_id = request.session.get('competencia_id')
    if not comp_id:
        primera = Competition.objects.first()
        if primera:
            comp_id = primera.id
            request.session['competencia_id'] = comp_id
            
    # Manejo seguro si no hay competencias
    competencia_activa = None
    if comp_id:
        competencia_activa = get_object_or_404(Competition, id=comp_id)

    # --- 2. FILTRADO (Tu código + Adaptación al nuevo diseño) ---
    
    # Usamos 'mis_torneos' en el return para coincidir con el HTML nuevo
    mis_torneos_list = TournamentMember.objects.filter(
        user=request.user, 
        status='ACCEPTED',
        tournament__competition=competencia_activa # <--- ¡MANTENEMOS EL FILTRO!
    ).select_related('tournament').order_by('-joined_at')

    pendientes_list = TournamentMember.objects.filter(
        user=request.user, 
        status='PENDING',
        tournament__competition=competencia_activa # <--- ¡MANTENEMOS EL FILTRO!
    ).select_related('tournament').order_by('-joined_at')

    # Nota: Ya no procesamos el formulario aquí porque el botón "Crear"
    # del nuevo diseño lleva a una vista dedicada ('crear_torneo').

    return render(request, 'core/mis_torneos.html', {
        'mis_torneos': mis_torneos_list, 
        'pendientes': pendientes_list,
        'competencia_activa': competencia_activa
    })

@login_required
def buscar_torneo(request):
    query = request.GET.get('q')
    resultados = []

    if query:
        # Buscamos por Nombre o por Código exacto
        resultados = Tournament.objects.filter(
            Q(name_icontains=query) | Q(code_iexact=query)
        ).exclude(members=request.user) # Excluir los que ya estoy unido

    return render(request, 'core/buscar_torneo.html', {'resultados': resultados, 'query': query})

@login_required
def unirse_torneo(request, tournament_id):
    torneo = Tournament.objects.get(id=tournament_id)
    
    # Verificamos si ya existe la solicitud para no duplicar
    miembro, created = TournamentMember.objects.get_or_create(
        user=request.user,
        tournament=torneo
    )
    
    if created:
        miembro.status = 'PENDING' # Por defecto entra en espera
        miembro.save()
        messages.success(request, f'Solicitud enviada a "{torneo.name}". Espera que el admin te acepte.')
    else:
        messages.info(request, 'Ya has enviado una solicitud a este torneo.')
        
    return redirect('mis_torneos')
@login_required
def gestionar_torneo(request, tournament_id):
    torneo = get_object_or_404(Tournament, id=tournament_id)
    
    # SEGURIDAD: Solo el creador puede entrar aquí
    if request.user != torneo.creator:
        messages.error(request, "Solo el creador del torneo puede gestionarlo.")
        return redirect('mis_torneos')

    # Buscamos pendientes y aceptados
    pendientes = TournamentMember.objects.filter(tournament=torneo, status='PENDING')
    aceptados = TournamentMember.objects.filter(tournament=torneo, status='ACCEPTED')

    return render(request, 'core/gestionar_torneo.html', {
        'torneo': torneo,
        'pendientes': pendientes,
        'aceptados': aceptados
    })

@login_required
def responder_solicitud(request, member_id, accion):
    miembro = get_object_or_404(TournamentMember, id=member_id)
    torneo = miembro.tournament
    
    # SEGURIDAD: Solo el creador puede decidir
    if request.user != torneo.creator:
        messages.error(request, "No tienes permiso para hacer esto.")
        return redirect('mis_torneos')

    if accion == 'aceptar':
        miembro.status = 'ACCEPTED'
        miembro.save()
        messages.success(request, f"¡{miembro.user.username} ha sido aceptado en el torneo!")
        
    elif accion == 'rechazar':
        # Si rechazamos, borramos la solicitud para que pueda volver a intentar o simplemente desaparezca
        nombre = miembro.user.username
        miembro.delete()
        messages.warning(request, f"Solicitud de {nombre} rechazada.")

    # Volvemos al panel de gestión
    return redirect('gestionar_torneo', tournament_id=torneo.id)

@login_required
def eliminar_torneo(request, tournament_id):
    torneo = get_object_or_404(Tournament, id=tournament_id)
    
    # SEGURIDAD: Solo el creador puede borrarlo
    if request.user != torneo.creator:
        messages.error(request, "No tienes permiso para eliminar este torneo.")
        return redirect('mis_torneos')
    
    # Borramos el torneo (y a todos sus miembros en cascada)
    nombre = torneo.name
    torneo.delete()
    messages.success(request, f"El torneo '{nombre}' ha sido eliminado correctamente.")
    
    return redirect('mis_torneos')

# --- AGREGAR AL FINAL DE core/views.py ---
from django.core.management import call_command
from django.http import HttpResponse

def correr_migraciones_web(request):
    try:
        # 1. Le decimos a Django: "Fíjate qué cambios hubo en models.py" (Crea el archivo de migración)
        call_command('makemigrations')
        
        # 2. Le decimos: "Aplica esos cambios a la base de datos real"
        call_command('migrate')
        
        return HttpResponse("✅ ¡ÉXITO! Se agregó la columna 'points' y la base de datos está actualizada.")
    except Exception as e:
        return HttpResponse(f"❌ Error al migrar: {e}")
    
# --- AGREGAR AL FINAL DE core/views.py ---

# Asegúrate de tener estos imports arriba en views.py:
# from .models import Match, Team, Competition  <-- IMPORTANTE AGREGAR Competition
# import requests

# En core/views.py

def cargar_fixture_inicial(request, id_liga): # <--- AHORA RECIBE EL ID
    if not request.user.is_staff:
        return HttpResponse("⛔ Acceso denegado.")

    API_TOKEN = '1988cfde850245faaaceaf5d9ff33ada' 
    
    # YA NO ESTÁ FIJO. Usamos el que viene de la URL
    COMPETITION_ID_API = id_liga 
    
    headers = {'X-Auth-Token': API_TOKEN}
    url = f"https://api.football-data.org/v4/competitions/{COMPETITION_ID_API}/matches"

    log_html = f"<h1>📝 Reporte de Carga (Liga ID: {id_liga})</h1><ul>"
    actualizados = 0
    nuevos = 0

    try:
        try:
            competencia_db = Competition.objects.get(api_id=COMPETITION_ID_API)
        except Competition.DoesNotExist:
            return HttpResponse(f"❌ Error: No existe la competición con ID {COMPETITION_ID_API} en tu base de datos. <br>Ve al Admin y créala primero.")

        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'matches' in data:
            for item in data['matches']:
                
                # LOGICA UNIVERSAL (Sirve para Mundial, Premier, etc.)
                nombre_local = item['homeTeam']['name'] or "A Confirmar"
                nombre_visitante = item['awayTeam']['name'] or "A Confirmar"
                flag_local = item['homeTeam'].get('tla') or 'XX'
                flag_visitante = item['awayTeam'].get('tla') or 'XX'

                # 1. Equipos
                equipo_local, _ = Team.objects.get_or_create(
                    name=nombre_local, 
                    defaults={'logo': item['homeTeam'].get('crest'), 'flag_code': flag_local}
                )
                equipo_visitante, _ = Team.objects.get_or_create(
                    name=nombre_visitante, 
                    defaults={'logo': item['awayTeam'].get('crest'), 'flag_code': flag_visitante}
                )

                # 2. Datos
                fecha = item['utcDate']
                estado = item['status']
                gol_local = item['score']['fullTime']['home']
                gol_visitante = item['score']['fullTime']['away']
                
                ronda_api = item.get('matchday')
                nombre_ronda = f"Fecha {ronda_api}" if ronda_api else item.get('stage', 'General').replace('_', ' ').title()

                # 3. Guardar
                partido = Match.objects.filter(
                    competition=competencia_db, 
                    home_team=equipo_local, 
                    away_team=equipo_visitante
                ).first()

                if partido:
                    cambios = []
                    if partido.status != estado:
                        partido.status = estado
                        cambios.append("Estado")
                    if partido.home_goals != gol_local:
                        partido.home_goals = gol_local
                        partido.away_goals = gol_visitante
                        cambios.append("Goles")
                    
                    if cambios:
                        partido.save()
                        actualizados += 1
                        log_html += f"<li>✅ <b>{equipo_local} vs {equipo_visitante}</b>: Actualizado</li>"
                else:
                    Match.objects.create(
                        competition=competencia_db,
                        home_team=equipo_local,
                        away_team=equipo_visitante,
                        date=fecha,
                        status=estado,
                        round_name=nombre_ronda,
                        home_goals=gol_local,
                        away_goals=gol_visitante
                    )
                    nuevos += 1
                    log_html += f"<li>🆕 <b>{equipo_local} vs {equipo_visitante}</b>: Creado</li>"

            log_html += f"</ul><h2>Resumen: {nuevos} Nuevos, {actualizados} Actualizados.</h2>"
            return HttpResponse(log_html)
        
        else:
            return HttpResponse(f"⚠️ La API respondió sin partidos. Data: {data}")

    except Exception as e:
        return HttpResponse(f"❌ Error crítico: {e}")
    
def cambiar_competencia(request, comp_id):
    # 1. Guardamos la elección con fuerza
    request.session['competencia_id'] = comp_id
    request.session.modified = True # Asegura que se guarde
    
    # 2. Detectamos de dónde viene el clic
    referer = request.META.get('HTTP_REFERER', '')
    
    print(f"🔄 Cambiando a Liga ID {comp_id}. Vengo de: {referer}") # Para depurar

    # 3. Redirecciones inteligentes
    if 'fixture' in referer: 
        return redirect('fixture')
    
    if 'tabla' in referer: 
        return redirect('tabla')
    
    # Si estamos en CUALQUIER página de pronósticos o predicción
    if 'pronosticos' in referer or 'predecir' in referer: 
        return redirect('pronosticos_liga', competition_id=comp_id)
    
    # Por defecto al Home
    return redirect('home')

# En core/views.py

# En core/views.py

def fixture(request):
    # 1. Competencia Activa
    comp_id = request.session.get('competencia_id')
    if not comp_id:
        first_comp = Competition.objects.first()
        if first_comp:
            comp_id = first_comp.id
            request.session['competencia_id'] = comp_id
    
    competencia_activa = None
    partidos = Match.objects.none()
    
    if comp_id:
        competencia_activa = Competition.objects.get(id=comp_id)
        # Filtramos por competencia
        partidos = Match.objects.filter(competition_id=comp_id).order_by('date')

    # 2. Agrupar Partidos para el Menú
    grupos_temp = {}
    rondas_nombres = [] 

    for partido in partidos:
        ronda = partido.round_name
        if ronda not in grupos_temp:
            grupos_temp[ronda] = []
            rondas_nombres.append(ronda)
        
        # En Fixture NO necesitamos predicciones, así que guardamos solo el partido
        item = { 'partido': partido }
        grupos_temp[ronda].append(item)

    # 3. Lógica del Selector de Fechas
    ronda_seleccionada = request.GET.get('ronda')

    # Si no eligió nada, buscamos la más cercana a HOY
    if not ronda_seleccionada and rondas_nombres:
        hoy = timezone.now()
        partido_futuro = partidos.filter(date__gte=hoy).first()
        
        if partido_futuro:
            ronda_seleccionada = partido_futuro.round_name
        else:
            ronda_seleccionada = rondas_nombres[-1]

    # Obtenemos los partidos de esa fecha específica
    grupo_activo = []
    if ronda_seleccionada and ronda_seleccionada in grupos_temp:
        grupo_activo = grupos_temp[ronda_seleccionada]
    
    # Ordenamos por horario
    grupo_activo.sort(key=lambda x: x['partido'].date)

    return render(request, 'core/fixture.html', {
        'competencia_activa': competencia_activa,
        'rondas_disponibles': rondas_nombres,
        'ronda_actual': ronda_seleccionada,
        'partidos_mostrar': grupo_activo
    })

def cargar_tabla(request, id_liga):
    if not request.user.is_staff:
        return HttpResponse("⛔ Acceso denegado.")

    API_TOKEN = '1988cfde850245faaaceaf5d9ff33ada' 
    headers = {'X-Auth-Token': API_TOKEN}
    url = f"https://api.football-data.org/v4/competitions/{id_liga}/standings"

    log_html = f"<h1>📊 Cargando Tabla (Liga: {id_liga})</h1><ul>"
    
    try:
        try:
            competencia_db = Competition.objects.get(api_id=id_liga)
        except Competition.DoesNotExist:
            return HttpResponse(f"❌ Error: No existe la competición {id_liga}. Carga primero el fixture.")

        # Limpiamos tabla anterior
        Standing.objects.filter(competition=competencia_db).delete()

        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'standings' in data:
            for bloque in data['standings']:
                if bloque['type'] == 'TOTAL':
                    
                    # --- CORRECCIÓN CLAVE PARA LIGAS ---
                    # En ligas, 'group' viene como None. Validamos antes de usar replace.
                    raw_group = bloque.get('group')
                    if raw_group:
                        nombre_grupo = raw_group.replace('_', ' ') # Ej: GROUP A
                    else:
                        nombre_grupo = "General" # Para Premier, Bundesliga, etc.
                    # -----------------------------------
                    
                    for row in bloque['table']:
                        equipo_api = row['team']
                        nombre_equipo = equipo_api['name'] or "A Confirmar"

                        # Buscamos o creamos el equipo
                        team_obj, _ = Team.objects.get_or_create(
                            name=nombre_equipo,
                            defaults={
                                'logo': equipo_api.get('crest'),
                                'flag_code': 'XX'
                            }
                        )

                        Standing.objects.create(
                            competition=competencia_db,
                            team=team_obj,
                            position=row['position'],
                            played=row['playedGames'],
                            won=row['won'],
                            drawn=row['draw'],
                            lost=row['lost'],
                            points=row['points'],
                            goals_for=row['goalsFor'],
                            goals_against=row['goalsAgainst'],
                            goal_diff=row['goalDifference'],
                            group=nombre_grupo
                        )
                        log_html += f"<li>✅ {row['position']}° {team_obj.name} ({row['points']} pts)</li>"

            return HttpResponse(log_html + "</ul>")
        else:
            return HttpResponse(f"⚠️ La API no devolvió tablas. Data: {data}")

    except Exception as e:
        return HttpResponse(f"❌ Error crítico: {e}")

def tabla_posiciones(request):
    # 1. Obtener Liga Activa
    comp_id = request.session.get('competencia_id')
    if not comp_id:
        first = Competition.objects.first()
        if first:
            comp_id = first.id
            request.session['competencia_id'] = comp_id
            
    # 2. Buscar datos
    standings = []
    competencia = None
    
    if comp_id:
        competencia = Competition.objects.get(id=comp_id)
        # Traemos la tabla ordenada por Grupo y luego por Posición
        standings = Standing.objects.filter(competition_id=comp_id).order_by('group', 'position')

    # 3. Agrupar para el HTML (Para que se vea separado por grupos)
    # Usamos itertools.groupby que es muy eficiente para esto
    from itertools import groupby
    
    # Convertimos a lista de diccionarios: [ {'nombre': 'GROUP A', 'equipos': [...]}, ... ]
    tabla_agrupada = []
    for key, group in groupby(standings, key=lambda x: x.group):
        tabla_agrupada.append({
            'nombre_grupo': key,
            'equipos': list(group)
        })

    return render(request, 'core/tabla.html', {
        'tabla_agrupada': tabla_agrupada,
        'competencia': competencia
    })


@staff_member_required
def debug_datos(request):
    comps = Competition.objects.all()
    
    html = """
    <body style='font-family: sans-serif; padding: 20px; background: #f0f0f0;'>
    <h1>🕵️‍♂️ Detective de Datos</h1>
    <div style='background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);'>
    """
    
    # 1. ¿Qué estás viendo tú ahora?
    sess_id = request.session.get('competencia_id')
    html += f"<h3>🔑 Tu Sesión Actual</h3><p>Estás "
    
    if sess_id:
        try:
            actual = Competition.objects.get(id=sess_id)
            html += f"viendo la liga: <b>{actual.name}</b> (ID Interno: <b>{actual.id}</b> | API ID: <b>{actual.api_id}</b>)"
        except:
            html += f"apuntando a una ID que ya no existe: <b>{sess_id}</b>"
    else:
        html += "sin ninguna liga seleccionada (None)."
    
    html += "</p><hr>"

    # 2. ¿Dónde están los partidos realmente?
    html += "<h3>📚 Inventario de Ligas</h3><ul>"
    for c in comps:
        qty = Match.objects.filter(competition=c).count()
        color = "green" if qty > 0 else "red"
        select_btn = f" <a href='/cambiar-liga/{c.id}/' style='text-decoration:none; background:#333; color:white; padding:2px 8px; border-radius:4px; font-size:12px;'>👉 Seleccionar</a>"
        
        html += f"<li style='margin-bottom: 10px; color:{color};'>"
        html += f"🏆 <b>{c.name}</b> (ID: {c.id} | API_ID: {c.api_id}) <br>"
        html += f"&nbsp;&nbsp;&nbsp;&nbsp;➡ Tiene <b>{qty}</b> partidos cargados. {select_btn}</li>"
        
    html += "</ul></div></body>"
    return HttpResponse(html)

@login_required
def crear_torneo(request):
    # Recuperamos la competencia igual que siempre
    comp_id = request.session.get('competencia_id')
    competencia_activa = get_object_or_404(Competition, id=comp_id)

    if request.method == 'POST':
        # Validamos límite de 3 torneos (Tu lógica original)
        cantidad_creados = Tournament.objects.filter(creator=request.user, competition=competencia_activa).count()
        
        if cantidad_creados >= 3:
            messages.error(request, "🚫 Límite alcanzado: Solo 3 torneos por liga.")
            return redirect('mis_torneos')

        form = TournamentForm(request.POST)
        if form.is_valid():
            torneo = form.save(commit=False)
            torneo.creator = request.user
            torneo.competition = competencia_activa # Asignación automática
            torneo.save()
            
            # Crear la membresía del creador automáticamente
            TournamentMember.objects.create(
                user=request.user, 
                tournament=torneo, 
                status='ACCEPTED'
            )
            
            messages.success(request, f'¡Torneo "{torneo.name}" creado!')
            return redirect('mis_torneos')
    else:
        form = TournamentForm()

    return render(request, 'core/crear_torneo.html', {
        'form': form,
        'competencia': competencia_activa
    })

# En core/views.py

@login_required
def unirse_por_codigo(request):
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        
        # 1. Buscamos si existe un torneo con ese código
        try:
            torneo = Tournament.objects.get(code=codigo)
        except Tournament.DoesNotExist:
            messages.error(request, "❌ Código inválido. No encontramos ese torneo.")
            return redirect('unirse_por_codigo')

        # 2. Verificamos si ya es miembro
        if TournamentMember.objects.filter(user=request.user, tournament=torneo).exists():
            messages.warning(request, f"Ya eres parte de {torneo.name}.")
            return redirect('mis_torneos')

        # 3. Lo unimos (Si el torneo es privado podrías ponerlo como PENDING, aquí lo aceptamos directo o según tu lógica)
        TournamentMember.objects.create(
            user=request.user, 
            tournament=torneo, 
            status='ACCEPTED' # O 'PENDING' si quieres aprobación del admin
        )
        
        messages.success(request, f"✅ ¡Te uniste a {torneo.name} exitosamente!")
        return redirect('mis_torneos')

    return render(request, 'core/unirse_por_codigo.html')

@login_required
def detalle_torneo(request, tournament_id):
    # Buscamos el torneo o damos error 404
    torneo = get_object_or_404(Tournament, id=tournament_id)
    
    # Buscamos los miembros aceptados y los ordenamos por puntos (mayor a menor)
    ranking = TournamentMember.objects.filter(
        tournament=torneo, 
        status='ACCEPTED'
    ).select_related('user').order_by('-points')

    return render(request, 'core/detalle_torneo.html', {
        'torneo': torneo,
        'ranking': ranking
    })


def crear_admin_emergencia(request):
    # Verificamos si ya existe para no dar error
    if not User.objects.filter(username='admin').exists():
        # CREA EL SUPERUSUARIO
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        return HttpResponse("✅ ¡Usuario 'admin' creado con contraseña 'admin123'! Entra a /admin")
    else:
        return HttpResponse("⚠️ El usuario 'admin' ya existe.")
    
@login_required
def perfil_usuario(request):
    # 1. Estadísticas Globales
    mis_preds = Prediction.objects.filter(user=request.user)
    
    total_pronosticos = mis_preds.count()
    total_puntos = mis_preds.aggregate(Sum('points'))['points__sum'] or 0
    
    # Plenos (3 puntos) vs Tendencias (1 punto)
    plenos = mis_preds.filter(points=3).count()
    tendencias = mis_preds.filter(points=1).count()
    fallos = mis_preds.filter(points=0).count() # Ojo: esto incluye partidos no jugados si se guardan con 0
    
    # Calcular efectividad real (Solo sobre partidos terminados)
    # Filtramos partidos que YA se jugaron (status='FINISHED')
    preds_terminadas = mis_preds.filter(match__status='FINISHED')
    jugados_count = preds_terminadas.count()
    
    efectividad = 0
    promedio = 0
    if jugados_count > 0:
        aciertos_totales = preds_terminadas.exclude(points=0).count()
        efectividad = int((aciertos_totales / jugados_count) * 100)
        promedio = round(total_puntos / jugados_count, 2)

    context = {
        'total_pronosticos': total_pronosticos,
        'total_puntos': total_puntos,
        'plenos': plenos,
        'tendencias': tendencias,
        'efectividad': efectividad,
        'promedio': promedio,
        'jugados_count': jugados_count
    }
    return render(request, 'core/perfil.html', context)

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        form = EditarPerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Tus datos han sido actualizados.")
            return redirect('perfil')
    else:
        form = EditarPerfilForm(instance=request.user)
    
    return render(request, 'core/editar_perfil.html', {'form': form})

# 2. VISTA: Gestionar Contraseña (La mágica ✨)
@login_required
def configurar_password(request):
    # Si el usuario ya tiene contraseña (login normal), usamos PasswordChangeForm
    # Si entró con Google (no tiene usable password), usamos SetPasswordForm
    
    if request.user.has_usable_password():
        FormularioPassword = PasswordChangeForm
        titulo = "Cambiar Contraseña"
    else:
        FormularioPassword = SetPasswordForm
        titulo = "Crear Contraseña"

    if request.method == 'POST':
        form = FormularioPassword(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # IMPORTANTE: Esto evita que se cierre la sesión al cambiar la clave
            update_session_auth_hash(request, user) 
            messages.success(request, "🔐 ¡Contraseña actualizada correctamente!")
            return redirect('perfil')
        else:
            messages.error(request, "Por favor corrige los errores abajo.")
    else:
        form = FormularioPassword(request.user)

    return render(request, 'core/password.html', {
        'form': form, 
        'titulo': titulo,
        'tiene_pass': request.user.has_usable_password()
    })

@login_required
def pronosticos_general(request):
    """
    Esta vista maneja el clic en el botón 'Pronósticos' del menú principal.
    """
    # 1. ¿El usuario ya tiene una liga en memoria?
    comp_id = request.session.get('competencia_id')
    
    # 2. Si NO tiene, buscamos la primera disponible (Por defecto)
    if not comp_id:
        primera = Competition.objects.first()
        if primera:
            comp_id = primera.id
            # ¡Importante! La guardamos en sesión para que quede seleccionada
            request.session['competencia_id'] = comp_id 
    
    # 3. Redirigimos a la liga (ya sea la de memoria o la por defecto)
    if comp_id:
        return redirect('pronosticos_liga', competition_id=comp_id)
    else:
        # Caso extremo: No hay ninguna liga cargada en el sistema
        return render(request, 'core/pronosticos.html', {'competencia_activa': None})
@login_required
def pronosticos_liga(request, competition_id):
    """
    Esta es la función principal de pronósticos con ID.
    """
    request.session['competencia_id'] = competition_id # Guardar en memoria
    competencia_activa = get_object_or_404(Competition, id=competition_id)
    
    partidos = Match.objects.filter(competition=competencia_activa).order_by('date')

    # Agrupación por Rondas
    grupos_temp = {}
    rondas_nombres = [] 
    for partido in partidos:
        ronda = partido.round_name
        if ronda not in grupos_temp:
            grupos_temp[ronda] = []
            rondas_nombres.append(ronda)
        
        pred = Prediction.objects.filter(user=request.user, match=partido).first()
        grupos_temp[ronda].append({'partido': partido, 'prediccion': pred})

    # Selector de Fecha
    ronda_seleccionada = request.GET.get('ronda')
    if not ronda_seleccionada and rondas_nombres:
        hoy = timezone.now()
        partido_futuro = partidos.filter(date__gte=hoy).first()
        ronda_seleccionada = partido_futuro.round_name if partido_futuro else rondas_nombres[-1]

    grupo_activo = grupos_temp.get(ronda_seleccionada, [])
    grupo_activo.sort(key=lambda x: x['partido'].date)

    return render(request, 'core/pronosticos.html', {
        'competencia_activa': competencia_activa,
        'rondas_disponibles': rondas_nombres,
        'ronda_actual': ronda_seleccionada,
        'partidos_mostrar': grupo_activo
    })