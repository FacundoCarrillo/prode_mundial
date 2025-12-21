from .models import Competition

def selector_competencias(request):
    # 1. Obtenemos todas las ligas para el menú desplegable
    todas_comps = Competition.objects.all()
    
    # 2. Buscamos cuál está seleccionada en la sesión
    comp_id = request.session.get('competencia_id')
    
    competencia_activa = None
    if comp_id:
        competencia_activa = Competition.objects.filter(id=comp_id).first()
    
    # Si no hay ninguna seleccionada (primera vez), elegimos la primera por defecto
    if not competencia_activa and todas_comps.exists():
        competencia_activa = todas_comps.first()
        # La guardamos en sesión para la próxima
        request.session['competencia_id'] = competencia_activa.id

    return {
        'lista_competencias': todas_comps,
        'competencia_activa': competencia_activa
    }