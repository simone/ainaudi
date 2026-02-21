"""
URL configuration for notifications admin endpoints.

All endpoints require elevated permissions (admin/delegato).
"""
from django.urls import path

from . import views_admin

urlpatterns = [
    path(
        'assignments/start-notifications/',
        views_admin.StartAssignmentNotificationsView.as_view(),
        name='admin-start-notifications'
    ),
    path('events/', views_admin.EventCreateView.as_view(), name='admin-event-create'),
    path('events/<uuid:event_id>/', views_admin.EventUpdateView.as_view(), name='admin-event-update'),
]
