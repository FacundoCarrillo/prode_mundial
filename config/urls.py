"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from core.views import home, predecir_partido # <--- Importamos la nueva vista
from core.views import home, predecir_partido, ranking  # <--- Agregamos ranking
from django.urls import path, include # <--- Agrega include aquí
from core.views import home, predecir_partido, ranking, actualizar_partidos_web, mis_torneos, buscar_torneo, unirse_torneo, gestionar_torneo, responder_solicitud, eliminar_torneo # <--- Importala

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- CAMBIO AQUÍ ---
    # Reemplazamos la línea vieja por esta nueva.
    # 'allauth.urls' maneja Login, Logout, Registro y... ¡GOOGLE!
    path('accounts/', include('allauth.urls')),

    path('', home, name='home'),
    path('predecir/<int:match_id>/', predecir_partido, name='predecir'),
    path('ranking/<int:tournament_id>/', ranking, name='ranking_torneo'),
    path('actualizar-ahora/', actualizar_partidos_web, name='actualizar_web'),
    path('mis-torneos/', mis_torneos, name='mis_torneos'),
    path('buscar-torneo/', buscar_torneo, name='buscar_torneo'),
    path('unirse/<int:tournament_id>/', unirse_torneo, name='unirse_torneo'),
    # Panel de control del dueño del torneo
    path('torneo/<int:tournament_id>/gestionar/', gestionar_torneo, name='gestionar_torneo'),
    
    # Acción de aceptar/rechazar (recibe el ID del MIEMBRO, no del torneo)
    path('solicitud/<int:member_id>/<str:accion>/', responder_solicitud, name='responder_solicitud'),
    path('torneo/<int:tournament_id>/eliminar/', eliminar_torneo, name='eliminar_torneo'),
]