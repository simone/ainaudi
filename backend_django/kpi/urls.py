"""
KPI URL configuration.
Only exposes endpoints needed by the frontend.
"""
from django.urls import path
from .views import KPIDatiView, KPISezioniView

urlpatterns = [
    path('dati', KPIDatiView.as_view(), name='kpi-dati'),
    path('sezioni', KPISezioniView.as_view(), name='kpi-sezioni'),
]
