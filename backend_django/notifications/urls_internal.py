"""
URL configuration for internal endpoints (called by Cloud Tasks).

No JWT auth - uses App Engine headers or shared secret.
"""
from django.urls import path

from . import views_internal

urlpatterns = [
    path('send-notification/', views_internal.SendNotificationView.as_view(), name='internal-send-notification'),
]
