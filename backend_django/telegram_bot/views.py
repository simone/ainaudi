"""
Telegram webhook controller and management views.

Receives Telegram updates via webhook, validates them, and dispatches
to the appropriate handler based on update type.
"""
import hashlib
import hmac
import logging
import time

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
import json

from . import telegram_client
from .models import TelegramUpdateLog
from .handlers import handle_update

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    """
    Receives Telegram webhook updates.

    POST /api/telegram/webhook/
    Telegram sends JSON updates here. Validated via secret token header.
    """

    # Simple in-memory rate limiter: {ip: [timestamps]}
    _rate_cache: dict[str, list[float]] = {}
    RATE_LIMIT = 60  # max requests per minute per IP

    def post(self, request):
        # Verify webhook secret
        if not self._verify_secret(request):
            logger.warning("Telegram webhook: invalid secret token")
            return JsonResponse({'error': 'forbidden'}, status=403)

        # Rate limiting
        ip = request.META.get('REMOTE_ADDR', '')
        if self._is_rate_limited(ip):
            logger.warning("Telegram webhook rate limited: ip=%s", ip)
            return JsonResponse({'error': 'rate limited'}, status=429)

        # Parse update
        try:
            update = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            logger.warning("Telegram webhook: invalid JSON body")
            return JsonResponse({'error': 'invalid json'}, status=400)

        update_id = update.get('update_id')
        if not update_id:
            return JsonResponse({'error': 'missing update_id'}, status=400)

        # Idempotency check
        if TelegramUpdateLog.objects.filter(update_id=update_id).exists():
            logger.debug("Telegram webhook: duplicate update_id=%s, skipping", update_id)
            return JsonResponse({'ok': True})

        # Extract common metadata for logging
        message = update.get('message', {})
        tg_user_id = message.get('from', {}).get('id')
        chat_id = message.get('chat', {}).get('id')

        # Process update
        try:
            handle_update(update)
            TelegramUpdateLog.objects.create(
                update_id=update_id,
                telegram_user_id=tg_user_id,
                chat_id=chat_id,
                update_type=self._classify_update(update),
                processing_status=TelegramUpdateLog.ProcessingStatus.OK,
            )
        except Exception as e:
            logger.error(
                "Telegram update processing failed: update_id=%s tg_user=%s error=%s",
                update_id, tg_user_id, e,
                exc_info=True,
            )
            TelegramUpdateLog.objects.create(
                update_id=update_id,
                telegram_user_id=tg_user_id,
                chat_id=chat_id,
                update_type=self._classify_update(update),
                processing_status=TelegramUpdateLog.ProcessingStatus.ERROR,
                error_message=str(e)[:500],
            )

        # Always return 200 to Telegram to prevent retries
        return JsonResponse({'ok': True})

    def _verify_secret(self, request) -> bool:
        """Verify the X-Telegram-Bot-Api-Secret-Token header."""
        expected = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
        if not expected:
            # No secret configured = accept all (dev mode)
            return True
        actual = request.META.get('HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN', '')
        return hmac.compare_digest(actual, expected)

    def _is_rate_limited(self, ip: str) -> bool:
        """Simple sliding window rate limiter."""
        now = time.time()
        window = 60  # seconds
        timestamps = self._rate_cache.get(ip, [])
        timestamps = [t for t in timestamps if now - t < window]
        if len(timestamps) >= self.RATE_LIMIT:
            return True
        timestamps.append(now)
        self._rate_cache[ip] = timestamps
        return False

    @staticmethod
    def _classify_update(update: dict) -> str:
        """Classify the type of Telegram update for logging."""
        msg = update.get('message', {})
        if msg.get('contact'):
            return 'contact'
        text = msg.get('text', '')
        if text.startswith('/'):
            return f'command:{text.split()[0]}'
        if text:
            return 'text'
        # Non-text content types
        for content_type in ('photo', 'video', 'audio', 'voice', 'document', 'sticker', 'location'):
            if msg.get(content_type):
                return content_type
        return 'unknown'


class TelegramSetupView(APIView):
    """
    Admin-only endpoint to manage Telegram bot setup.

    POST /api/telegram/setup/webhook/  — register webhook with Telegram
    DELETE /api/telegram/setup/webhook/ — remove webhook
    POST /api/telegram/setup/commands/ — register bot commands
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        action = request.data.get('action', 'webhook')

        if action == 'webhook':
            webhook_url = request.data.get('url')
            if not webhook_url:
                return Response(
                    {'error': 'url required'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
            result = telegram_client.set_webhook(webhook_url, secret_token=secret or None)
            if result is not None:
                telegram_client.set_my_commands()
                return Response({'ok': True, 'message': 'Webhook registered'})
            return Response(
                {'ok': False, 'message': 'Failed to set webhook'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if action == 'commands':
            result = telegram_client.set_my_commands()
            if result is not None:
                return Response({'ok': True, 'message': 'Commands registered'})
            return Response(
                {'ok': False, 'message': 'Failed to set commands'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {'error': f'Unknown action: {action}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def delete(self, request):
        result = telegram_client.delete_webhook()
        if result is not None:
            return Response({'ok': True, 'message': 'Webhook removed'})
        return Response(
            {'ok': False, 'message': 'Failed to delete webhook'},
            status=status.HTTP_502_BAD_GATEWAY,
        )
