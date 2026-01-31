"""
KPI URL configuration.
"""
from django.urls import path
from .views import (
    KPIDashboardView,
    KPITurnoutView,
    KPISectionStatusView,
    KPIIncidentsView,
)

urlpatterns = [
    path('dashboard/', KPIDashboardView.as_view(), name='kpi-dashboard'),
    path('turnout/', KPITurnoutView.as_view(), name='kpi-turnout'),
    path('sections/', KPISectionStatusView.as_view(), name='kpi-sections'),
    path('incidents/', KPIIncidentsView.as_view(), name='kpi-incidents'),
]
