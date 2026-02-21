"""
URL patterns for Campaign email templates and mass email.

Mounted at /api/rdl/ in main urls.py alongside rdl_registration_urlpatterns.
"""
from django.urls import path

from .views import (
    EmailTemplateListView,
    EmailTemplateDetailView,
    EmailTemplatePreviewView,
    EmailTemplateTestSendView,
    EmailTemplatePreviewInlineView,
    EmailTemplateVariablesView,
    MassEmailRecipientsInfoView,
    MassEmailSendView,
    MassEmailProgressView,
)

email_template_urlpatterns = [
    # Email Templates CRUD
    path('email-templates/', EmailTemplateListView.as_view(), name='email-template-list'),
    path('email-templates/variables/', EmailTemplateVariablesView.as_view(), name='email-template-variables'),
    path('email-templates/preview-inline/', EmailTemplatePreviewInlineView.as_view(), name='email-template-preview-inline'),
    path('email-templates/<int:pk>/', EmailTemplateDetailView.as_view(), name='email-template-detail'),
    path('email-templates/<int:pk>/preview/', EmailTemplatePreviewView.as_view(), name='email-template-preview'),
    path('email-templates/<int:pk>/test-send/', EmailTemplateTestSendView.as_view(), name='email-template-test-send'),

    # Mass Email
    path('mass-email/recipients-info/', MassEmailRecipientsInfoView.as_view(), name='mass-email-recipients-info'),
    path('mass-email/send/', MassEmailSendView.as_view(), name='mass-email-send'),
    path('mass-email/progress/<str:task_id>/', MassEmailProgressView.as_view(), name='mass-email-progress'),
]
