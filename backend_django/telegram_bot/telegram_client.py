"""
Telegram Bot API client.

Wraps HTTP calls to the Telegram Bot API for sending messages,
setting webhooks, and managing reply keyboards.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = 'https://api.telegram.org/bot{token}'


def _api_url(method: str) -> str:
    token = settings.TELEGRAM_BOT_TOKEN
    return f'{TELEGRAM_API_BASE.format(token=token)}/{method}'


def _call(method: str, payload: dict, timeout: int = 10) -> dict | None:
    """Make an API call to Telegram. Returns the result dict or None on error."""
    url = _api_url(method)
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        data = resp.json()
        if not data.get('ok'):
            logger.error(
                "Telegram API error method=%s status=%s description=%s",
                method, resp.status_code, data.get('description'),
            )
            return None
        return data.get('result')
    except requests.RequestException as e:
        logger.error("Telegram API request failed method=%s error=%s", method, e)
        return None


def send_message(chat_id: int, text: str, reply_markup: dict | None = None) -> dict | None:
    """Send a text message to a Telegram chat."""
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    return _call('sendMessage', payload)


def send_contact_request_keyboard(chat_id: int, text: str) -> dict | None:
    """Send a message with a reply keyboard requesting the user's phone number."""
    keyboard = {
        'keyboard': [[{
            'text': 'Condividi il mio numero',
            'request_contact': True,
        }]],
        'resize_keyboard': True,
        'one_time_keyboard': True,
    }
    return send_message(chat_id, text, reply_markup=keyboard)


def remove_keyboard(chat_id: int, text: str) -> dict | None:
    """Send a message and remove any custom keyboard."""
    return send_message(chat_id, text, reply_markup={'remove_keyboard': True})


def set_webhook(url: str, secret_token: str | None = None) -> dict | None:
    """Register a webhook URL with Telegram."""
    payload = {'url': url}
    if secret_token:
        payload['secret_token'] = secret_token
    return _call('setWebhook', payload)


def delete_webhook() -> dict | None:
    """Remove the current webhook."""
    return _call('deleteWebhook', {})


def set_my_commands() -> dict | None:
    """Register bot commands shown in the Telegram menu."""
    commands = [
        {'command': 'start', 'description': 'Avvia il bot'},
        {'command': 'help', 'description': 'Mostra istruzioni'},
        {'command': 'whoami', 'description': 'Mostra la tua identità'},
        {'command': 'reset', 'description': 'Scollega il tuo account'},
    ]
    return _call('setMyCommands', {'commands': commands})
