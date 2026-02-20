"""
URL configuration for RDL service (scrutinio + risorse).

High-traffic endpoints used by RDLs on election day.
"""
from django.urls import path, include
from data.urls import scrutinio_urlpatterns

urlpatterns = [
    # Scrutinio (vote data entry)
    path('api/scrutinio/', include(scrutinio_urlpatterns)),

    # Risorse (FAQ, documenti)
    path('api/resources/', include('resources.urls')),
    path('api/risorse/', include('resources.urls')),
]
