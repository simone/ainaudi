"""
Firebase Cloud Messaging (FCM) integration for push notifications.

Sends push notifications to user devices and handles email fallback.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

# Lazy Firebase initialization
_firebase_app = None


def _load_credentials_from_secret_manager():
    """
    Load Firebase service account credentials from Secret Manager.

    Falls back gracefully if Secret Manager is not available.
    """
    try:
        import json
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        project = getattr(settings, 'GOOGLE_CLOUD_PROJECT',
                          getattr(settings, 'CLOUD_TASKS_PROJECT', 'ainaudi-prod'))
        secret_name = f'projects/{project}/secrets/firebase-credentials/versions/latest'
        response = client.access_secret_version(name=secret_name)
        cred_dict = json.loads(response.payload.data.decode('utf-8'))
        logger.info('Firebase credentials loaded from Secret Manager')
        return cred_dict
    except Exception as e:
        logger.debug(f'Secret Manager fallback not available: {e}')
        return None


def _init_firebase():
    """
    Initialize Firebase Admin SDK lazily.

    Credential resolution order:
    1. FIREBASE_CREDENTIALS_PATH env var (local JSON file)
    2. Secret Manager secret "firebase-credentials"
    3. Application Default Credentials (works on GCP with default SA)
    """
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = None

        # 1. Try explicit file path
        cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', '')
        if cred_path:
            cred = credentials.Certificate(cred_path)
            logger.info('Firebase credentials from file: %s', cred_path)

        # 2. Try Secret Manager
        if cred is None:
            cred_dict = _load_credentials_from_secret_manager()
            if cred_dict:
                cred = credentials.Certificate(cred_dict)

        # 3. Initialize (with cred or ADC fallback)
        if cred:
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            _firebase_app = firebase_admin.initialize_app()
            logger.info('Firebase initialized with Application Default Credentials')

        logger.info('Firebase Admin SDK initialized')
        return _firebase_app
    except Exception as e:
        logger.error(f'Failed to initialize Firebase: {e}')
        return None


def send_push(notification):
    """
    Send a push notification to all active device tokens for the user.

    Args:
        notification: Notification model instance

    Returns:
        bool: True if at least one push was delivered successfully
    """
    from notifications.models import DeviceToken

    _init_firebase()

    tokens = DeviceToken.objects.filter(
        user=notification.user,
        is_active=True,
    ).values_list('id', 'token', named=True)

    if not tokens:
        logger.info(f'No active tokens for user {notification.user.email}')
        return False

    try:
        from firebase_admin import messaging
    except ImportError:
        logger.error('firebase_admin not installed')
        return False

    success_count = 0

    for device in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=notification.title,
                    body=notification.body,
                ),
                data={
                    'deep_link': notification.deep_link,
                    'notification_id': str(notification.id),
                    'type': notification.source_type,
                },
                token=device.token,
                webpush=messaging.WebpushConfig(
                    fcm_options=messaging.WebpushFCMOptions(
                        link=notification.deep_link,
                    ),
                ),
            )

            messaging.send(message)
            success_count += 1
            logger.info(
                f'Push sent to {notification.user.email} '
                f'(token {device.token[:20]}...)'
            )

        except messaging.UnregisteredError:
            # Token is no longer valid
            logger.warning(f'Token unregistered, deactivating: {device.token[:20]}...')
            DeviceToken.objects.filter(pk=device.id).update(is_active=False)

        except messaging.InvalidArgumentError as e:
            logger.warning(f'Invalid token, deactivating: {device.token[:20]}... ({e})')
            DeviceToken.objects.filter(pk=device.id).update(is_active=False)

        except Exception as e:
            logger.error(f'Push send failed for token {device.token[:20]}...: {e}')

    return success_count > 0


def send_push_to_token(token, title, body, data=None, ttl=None):
    """
    Send a push notification to a single FCM token.

    Used for test notifications and direct sends without a Notification model.

    Args:
        token: FCM registration token string
        title: notification title
        body: notification body
        data: optional dict of data payload
        ttl: optional time-to-live in seconds (notification expires after this)

    Returns:
        bool: True if sent successfully, False if token is invalid
    """
    _init_firebase()

    try:
        from firebase_admin import messaging
    except ImportError:
        logger.error('firebase_admin not installed')
        return False

    try:
        webpush_config = {}
        if ttl is not None:
            webpush_config['headers'] = {'TTL': str(ttl)}

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            webpush=messaging.WebpushConfig(**webpush_config) if webpush_config else None,
        )

        messaging.send(message)
        logger.info(f'Push sent to token {token[:20]}...')
        return True

    except (messaging.UnregisteredError, messaging.InvalidArgumentError) as e:
        logger.warning(f'Token invalid ({token[:20]}...): {e}')
        return False

    except Exception as e:
        logger.error(f'Push send failed ({token[:20]}...): {e}')
        return False


def send_email_notification(notification):
    """
    Send an email notification as fallback.

    Args:
        notification: Notification model instance

    Returns:
        bool: True if email was sent successfully
    """
    user = notification.user
    if not user.email:
        logger.warning(f'No email for user {user.pk}')
        return False

    try:
        # Build full URL for deep link
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        full_link = f'{frontend_url}{notification.deep_link}'

        # Try to render HTML template, fall back to plain text
        context = {
            'notification': notification,
            'user': user,
            'deep_link': full_link,
            'frontend_url': frontend_url,
        }

        try:
            html_message = render_to_string(
                'notifications/email/notification.html', context
            )
        except Exception:
            html_message = None

        text_message = (
            f'{notification.title}\n\n'
            f'{notification.body}\n\n'
            f'Apri: {full_link}\n'
        )

        send_mail(
            subject=notification.title,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f'Email sent to {user.email} for notification {notification.id}')
        return True

    except Exception as e:
        logger.error(f'Email send failed for {user.email}: {e}')
        return False
