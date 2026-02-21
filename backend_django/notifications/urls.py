"""
URL configuration for notifications user-facing endpoints.

All endpoints require JWT authentication.
"""
from django.urls import path

from . import views

urlpatterns = [
    path('dashboard', views.DashboardView.as_view(), name='me-dashboard'),
    path('events', views.EventListView.as_view(), name='me-events'),
    path('events/<uuid:event_id>', views.EventDetailView.as_view(), name='me-event-detail'),
    path('assignments', views.AssignmentListView.as_view(), name='me-assignments'),
    path('assignments/<int:assignment_id>', views.AssignmentDetailView.as_view(), name='me-assignment-detail'),
    path('device-tokens', views.DeviceTokenView.as_view(), name='me-device-tokens'),
    path('device-tokens/<uuid:token_id>', views.DeviceTokenView.as_view(), name='me-device-token-detail'),
]
