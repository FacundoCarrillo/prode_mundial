from django.shortcuts import render, redirect, get_object_or_404
from .models import Match, Prediction
from .forms import PredictionForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone # <--- IMPORTANTE

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
def ranking(request):
    # 1. Traemos a todos los usuarios
    usuarios = User.objects.all()
    lista_ranking = []

    # 2. Recorremos usuario por usuario para sumar sus puntos
    for usuario in usuarios:
        puntos_totales = 0
        # Buscamos todas las predicciones de este usuario
        predicciones = Prediction.objects.filter(user=usuario)

        for pred in predicciones:
            # Sumamos el resultado de get_score() (si devuelve None, sumamos 0)
            puntos_totales += pred.get_score() or 0

        # Guardamos al usuario y sus puntos en una lista temporal
        lista_ranking.append({
            'nombre': usuario.username,
            'puntos': puntos_totales
        })

    # 3. Ordenamos la lista de mayor a menor puntaje
    # lambda es una forma corta de decir: "ordena usando la clave 'puntos'"
    lista_ranking.sort(key=lambda x: x['puntos'], reverse=True)

    return render(request, 'core/ranking.html', {'ranking': lista_ranking})