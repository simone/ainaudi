"""
Management command per inviare email in bulk con rate limiting SES.

Amazon SES: 18 email/secondo (0.055 secondi tra email)

Usage:
    # Prova con 5 email
    python manage.py send_bulk_emails --recipients test@example.com test2@example.com --dry-run

    # Invia veramente
    python manage.py send_bulk_emails --recipients test@example.com test2@example.com

    # Leggi da file
    python manage.py send_bulk_emails --file recipients.txt

    # Con template
    python manage.py send_bulk_emails --file recipients.txt --template email/invite.html --context '{"event":"Elezioni 2026"}'
"""

import json
import time
from typing import List, Tuple

from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = "Invia email in bulk con rate limiting per Amazon SES (18 email/sec)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--recipients',
            nargs='+',
            help='Lista di email destinatari (es. test@example.com test2@example.com)'
        )
        parser.add_argument(
            '--file',
            help='File con email (una per riga, # per commenti)'
        )
        parser.add_argument(
            '--subject',
            default='Email da AINAUDI',
            help='Subject email'
        )
        parser.add_argument(
            '--message',
            default='Ciao, questa è una email di test.',
            help='Messaggio email'
        )
        parser.add_argument(
            '--template',
            help='Template Django da usare (es. email/invite.html)'
        )
        parser.add_argument(
            '--context',
            help='JSON context per il template (es. \'{"user": "Mario"}\')'
        )
        parser.add_argument(
            '--from-email',
            default='noreply@ainaudi.it',
            help='Email mittente'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Quante email prima di un delay più lungo'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula l\'invio senza inviare veramente'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Output verboso'
        )

    def handle(self, *args, **options):
        # Raccogli destinatari
        recipients = []

        if options['recipients']:
            recipients = options['recipients']
        elif options['file']:
            recipients = self._read_recipients_file(options['file'])
        else:
            raise CommandError("Usa --recipients o --file per specificare i destinatari")

        if not recipients:
            raise CommandError("Nessun destinatario trovato")

        # Prepara context per template
        context = {}
        if options['context']:
            try:
                context = json.loads(options['context'])
            except json.JSONDecodeError as e:
                raise CommandError(f"Context JSON invalido: {e}")

        # Costruisci email
        emails = []
        for recipient in recipients:
            subject = options['subject']

            if options['template']:
                message = render_to_string(options['template'], context)
            else:
                message = options['message']

            emails.append((
                subject,
                message,
                options['from_email'],
                [recipient.strip()]
            ))

        # Invia
        self._send_emails(emails, options['dry_run'], options['batch_size'], options['verbose'])

    def _read_recipients_file(self, filepath: str) -> List[str]:
        """Leggi email da file (una per riga)."""
        try:
            with open(filepath, 'r') as f:
                recipients = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.startswith('#')
                ]
            return recipients
        except FileNotFoundError:
            raise CommandError(f"File non trovato: {filepath}")

    def _send_emails(self, emails: List[Tuple], dry_run: bool, batch_size: int, verbose: bool):
        """Invia email con rate limiting."""
        total = len(emails)
        SES_RATE_LIMIT = 18  # email/sec
        DELAY = 1.0 / SES_RATE_LIMIT  # ~55ms

        self.stdout.write(
            self.style.SUCCESS(f"\n{'='*60}")
        )
        self.stdout.write(
            f"📧 AINAUDI Bulk Email Sender"
        )
        self.stdout.write(
            f"{'='*60}"
        )
        self.stdout.write(
            f"Destinatari: {total}"
        )
        self.stdout.write(
            f"SES Rate Limit: {SES_RATE_LIMIT} email/sec"
        )
        self.stdout.write(
            f"Tempo stimato: ~{total/SES_RATE_LIMIT:.0f}s"
        )
        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔒 DRY RUN - Nessuna email sarà inviata")
            )
        self.stdout.write(
            f"{'='*60}\n"
        )

        sent = 0
        failed = 0
        start_time = time.time()

        for i, (subject, message, from_email, recipient_list) in enumerate(emails, 1):
            recipient_str = ', '.join(recipient_list)

            if dry_run:
                self.stdout.write(f"[PREVIEW] [{i}/{total}] → {recipient_str}")
                sent += 1
            else:
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=from_email,
                        recipient_list=recipient_list,
                        fail_silently=False,
                    )
                    sent += 1
                    if verbose:
                        self.stdout.write(
                            self.style.SUCCESS(f"✓ [{i}/{total}] {recipient_str}")
                        )
                    else:
                        # Progress minimalista
                        if i % max(1, total // 10) == 0:
                            self.stdout.write(f"  {i}/{total}...")

                except Exception as e:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR(f"✗ [{i}/{total}] {recipient_str}: {str(e)}")
                    )

            # Rate limiting
            if i < total:
                time.sleep(DELAY)

                # Delay più lungo ogni batch_size
                if i % batch_size == 0 and not dry_run:
                    time.sleep(0.5)

        elapsed = time.time() - start_time

        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(
            self.style.SUCCESS(f"✓ Inviati: {sent}")
        )
        if failed > 0:
            self.stdout.write(
                self.style.ERROR(f"✗ Falliti: {failed}")
            )
        self.stdout.write(
            f"⏱  Tempo: {elapsed:.2f}s"
        )
        if sent > 0:
            self.stdout.write(
                f"⚡ Velocità: {sent/elapsed:.1f} email/sec"
            )
        self.stdout.write(f"{'='*60}\n")
