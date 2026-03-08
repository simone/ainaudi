"""
Telegram Bot URL configuration.
"""
from django.urls import path
from .views import TelegramWebhookView, TelegramSetupView

urlpatterns = [
    path('webhook/', TelegramWebhookView.as_view(), name='telegram-webhook'),
    path('setup/', TelegramSetupView.as_view(), name='telegram-setup'),
]
