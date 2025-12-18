from django.shortcuts import render, redirect, get_object_or_404
from .models import Match, Prediction, Team, Tournament, TournamentMember
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
from django.db.models import Sum
import requests
from datetime import timedelta

def home(request):
    # 1. Traemos todos los partidos
    partidos = Match.objects.all()
    
    # 2. Preparamos un diccionario rápido de predicciones del usuario
    predicciones_dict = {}
    if request.user.is_authenticated:
        predicciones = Prediction.objects.filter(user=request.user)
        # Creamos un diccionario { id_partido: objeto_prediccion }
        predicciones_dict = {p.match.id: p for p in predicciones}

    # 3. Armamos la lista FINAL combinada
    lista_final = []
    for partido in partidos:
        # Buscamos si hay predicción para este partido (será None si no hay)
        prediccion_usuario = predicciones_dict.get(partido.id)
        
        # Guardamos todo junto en un paquetito
        item = {
            'partido': partido,
            'prediccion': prediccion_usuario
        }
        lista_final.append(item)
            
    # Enviamos 'lista_partidos' en lugar de las dos variables sueltas
    return render(request, 'core/home.html', {'lista_partidos': lista_final})

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
            return redirect('home') # Lo mandamos al inicio
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
    API_TOKEN = 'TU_TOKEN_REAL_AQUI' # <--- REVISA QUE ESTÉ TU TOKEN PUESTO
    # --------------------------
    
    base_url = "https://api.football-data.org/v4/matches"
    headers = {'X-Auth-Token': API_TOKEN}
    
    # Rango de fechas
    hoy = timezone.now().date()
    ayer = hoy - timedelta(days=4)
    manana = hoy + timedelta(days=5)
    
    params = {
        'dateFrom': ayer.strftime('%Y-%m-%d'),
        'dateTo': manana.strftime('%Y-%m-%d')
    }

    reporte = [] # <--- Lista para guardar lo que vemos

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
                    home_team__name__icontains=local,
                    away_team__name__icontains=visitante
                ).first()

                if partido_db:
                    info_partido['accion'] = '✅ Actualizado'
                    
                    # Actualizar datos
                    if goles_local is not None:
                        partido_db.home_goals = goles_local
                        partido_db.away_goals = goles_visitante
                    
                    partido_db.date = item['utcDate']
                    partido_db.save()

                    # Calcular Puntos
                    preds = Prediction.objects.filter(match=partido_db)
                    puntos_repartidos = 0
                    
                    for pred in preds:
                        pts = 0
                        if pred.predicted_home == goles_local and pred.predicted_away == goles_visitante:
                            pts = 3
                        else:
                            # Lógica simple de ganador
                            winner_real = "H" if goles_local > goles_visitante else "A" if goles_visitante > goles_local else "D"
                            winner_pred = "H" if pred.predicted_home > pred.predicted_away else "A" if pred.predicted_away > pred.predicted_home else "D"
                            if winner_real == winner_pred:
                                pts = 1
                        
                        if pred.points != pts:
                            pred.points = pts
                            pred.save()
                            puntos_repartidos += 1
                            
                    if puntos_repartidos > 0:
                        info_partido['accion'] += f" y Puntos Recalculados ({puntos_repartidos} preds)"

                reporte.append(info_partido)

            # Recalcular Torneos Globalmente
            miembros = TournamentMember.objects.filter(status='ACCEPTED')
            for m in miembros:
                total = Prediction.objects.filter(user=m.user).aggregate(Sum('points'))['points__sum'] or 0
                if m.points != total:
                    m.points = total
                    m.save()

        else:
            messages.warning(request, "La API respondió OK pero sin partidos.")

    except Exception as e:
        messages.error(request, f"Error: {e}")
        return redirect('mis_torneos')

    # EN LUGAR DE REDIRIGIR, MOSTRAMOS EL REPORTE
    return render(request, 'core/actualizar_resultados.html', {'reporte': reporte})
    
@login_required
def mis_torneos(request):
    # 1. Torneos donde estoy jugando (ACEPTADO)
    jugando = TournamentMember.objects.filter(
        user=request.user, 
        status='ACCEPTED'
    ).select_related('tournament')

    # 2. Torneos donde espero aprobación (PENDIENTE)
    pendientes = TournamentMember.objects.filter(
        user=request.user, 
        status='PENDING'
    ).select_related('tournament')

    if request.method == 'POST':
        # --- NUEVA VALIDACIÓN: LÍMITE DE 3 TORNEOS ---
        cantidad_creados = Tournament.objects.filter(creator=request.user).count()
        
        if cantidad_creados >= 3:
            messages.error(request, "🚫 Límite alcanzado: Solo puedes administrar hasta 3 torneos a la vez.")
            # --- CORRECCIÓN AQUÍ: ---
            # Definimos el form aunque haya error, para que no falle el render de abajo.
            form = TournamentForm(request.POST) 
        # ---------------------------------------------
        else:
            # Si no llegó al límite, procesamos el formulario normalmente
            form = TournamentForm(request.POST)
            if form.is_valid():
                torneo = form.save(commit=False)
                torneo.creator = request.user
                torneo.save()
                
                TournamentMember.objects.create(
                    user=request.user, 
                    tournament=torneo, 
                    status='ACCEPTED'
                )
                messages.success(request, f'¡Torneo "{torneo.name}" creado!')
                return redirect('mis_torneos')
    else:
        form = TournamentForm()

    return render(request, 'core/mis_torneos.html', {
        'jugando': jugando,
        'pendientes': pendientes,
        'form': form
    })

@login_required
def buscar_torneo(request):
    query = request.GET.get('q')
    resultados = []
    
    if query:
        # Buscamos por Nombre o por Código exacto
        resultados = Tournament.objects.filter(
            Q(name__icontains=query) | Q(code__iexact=query)
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
