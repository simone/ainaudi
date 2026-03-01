"""
URL configuration for internal endpoints (called by Cloud Tasks).

No JWT auth - uses App Engine headers or shared secret.
"""
from django.urls import path

from . import views_internal

urlpatterns = [
    # Legacy: per-user notification sending
    path('send-notification/', views_internal.SendNotificationView.as_view(), name='internal-send-notification'),

    # New: event notifications (called once per offset, determines recipients dynamically)
    path('send-event-notifications/<uuid:event_id>/', views_internal.SendEventNotificationsView.as_view(), name='internal-send-event-notifications'),
]
