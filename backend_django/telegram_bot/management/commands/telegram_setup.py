"""
Management command for Telegram bot setup.

Usage:
    python manage.py telegram_setup webhook https://yourdomain.com/api/telegram/webhook/
    python manage.py telegram_setup commands
    python manage.py telegram_setup delete_webhook
    python manage.py telegram_setup info
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from telegram_bot import telegram_client


class Command(BaseCommand):
    help = 'Setup Telegram bot: register webhook, commands, etc.'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['webhook', 'commands', 'delete_webhook', 'info'],
            help='Action to perform',
        )
        parser.add_argument(
            'url',
            nargs='?',
            help='Webhook URL (required for "webhook" action)',
        )

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError('TELEGRAM_BOT_TOKEN is not set.')

        action = options['action']

        if action == 'webhook':
            url = options.get('url')
            if not url:
                raise CommandError('URL is required for webhook action.')
            secret = settings.TELEGRAM_WEBHOOK_SECRET or None
            result = telegram_client.set_webhook(url, secret_token=secret)
            if result is not None:
                self.stdout.write(self.style.SUCCESS(f'Webhook registered: {url}'))
                # Also register commands
                telegram_client.set_my_commands()
                self.stdout.write(self.style.SUCCESS('Bot commands registered.'))
            else:
                raise CommandError('Failed to set webhook.')

        elif action == 'commands':
            result = telegram_client.set_my_commands()
            if result is not None:
                self.stdout.write(self.style.SUCCESS('Bot commands registered.'))
            else:
                raise CommandError('Failed to register commands.')

        elif action == 'delete_webhook':
            result = telegram_client.delete_webhook()
            if result is not None:
                self.stdout.write(self.style.SUCCESS('Webhook removed.'))
            else:
                raise CommandError('Failed to remove webhook.')

        elif action == 'info':
            self.stdout.write(f'Bot token: {settings.TELEGRAM_BOT_TOKEN[:8]}...')
            self.stdout.write(f'Webhook secret: {"set" if settings.TELEGRAM_WEBHOOK_SECRET else "not set"}')
