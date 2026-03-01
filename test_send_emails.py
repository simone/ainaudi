#!/usr/bin/env python3
"""
Script per testare l'invio di email su Django con rate limiting SES.

Amazon SES limite: 18 email/secondo
Per 500 email: ~28 secondi

Usage:
    # Test con 5 email
    python manage.py shell < test_send_emails.py --num=5

    # Oppure esegui direttamente
    python3 test_send_emails.py --num=5 --to=test@example.com
"""

import os
import sys
import django
import time
import argparse
from typing import List, Tuple

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mass_mail, send_mail
from django.template.loader import render_to_string


class EmailSender:
    """Invia email in batch con rate limiting per Amazon SES."""

    # Amazon SES rate limit: 18 email/secondo
    SES_RATE_LIMIT = 18  # email/secondo
    DELAY_BETWEEN_EMAILS = 1.0 / SES_RATE_LIMIT  # ~55ms tra email

    def __init__(self, verbose=True):
        self.verbose = verbose
        self.sent = 0
        self.failed = 0
        self.start_time = None

    def log(self, msg):
        if self.verbose:
            print(f"[{time.time() - self.start_time:.2f}s] {msg}")

    def send_batch(self, emails: List[Tuple[str, str, str, List[str]]], batch_size=10):
        """
        Invia email in batch con delay per rispettare SES rate limit.

        Args:
            emails: Lista di tuple (subject, message, from_email, [to_emails])
            batch_size: Quante email inviare prima di fare un delay più lungo

        Returns:
            (sent, failed)
        """
        self.start_time = time.time()
        total = len(emails)

        self.log(f"Inizio invio: {total} email @ {self.SES_RATE_LIMIT}/sec (~{total/self.SES_RATE_LIMIT:.0f}s)")

        for i, email_tuple in enumerate(emails, 1):
            subject, message, from_email, recipient_list = email_tuple

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=from_email,
                    recipient_list=recipient_list,
                    fail_silently=False,
                )
                self.sent += 1
                self.log(f"✓ [{i}/{total}] Inviato a {', '.join(recipient_list)}")

            except Exception as e:
                self.failed += 1
                self.log(f"✗ [{i}/{total}] Errore: {str(e)}")

            # Rate limiting
            if i < total:  # Non fare delay dopo l'ultima email
                time.sleep(self.DELAY_BETWEEN_EMAILS)

                # Delay più lungo ogni batch_size email (per stabilità)
                if i % batch_size == 0:
                    self.log(f"⏸  Pausa tra batch ({i}/{total})")
                    time.sleep(0.5)

        self._print_summary()
        return self.sent, self.failed

    def _print_summary(self):
        elapsed = time.time() - self.start_time
        self.log(f"\n{'='*60}")
        self.log(f"✓ Inviati: {self.sent}")
        self.log(f"✗ Falliti: {self.failed}")
        self.log(f"⏱  Tempo totale: {elapsed:.2f}s")
        self.log(f"⚡ Velocità: {self.sent/elapsed:.1f} email/sec")
        self.log(f"{'='*60}\n")


def test_single_email(to_email: str = None):
    """Testa l'invio di una singola email."""
    print("\n🧪 TEST: Invio singola email")
    print("="*60)

    if not to_email:
        to_email = input("Inserisci email di test: ").strip()

    try:
        send_mail(
            subject="🧪 Test Email AINAUDI",
            message="Questo è un test dell'infrastruttura email.",
            from_email="noreply@ainaudi.it",
            recipient_list=[to_email],
            fail_silently=False,
        )
        print(f"✅ Email inviata a {to_email}")
        return True
    except Exception as e:
        print(f"❌ Errore: {e}")
        return False


def test_batch_emails(num: int = 5, to_email: str = None):
    """Testa l'invio di email in batch."""
    print(f"\n🧪 TEST: Invio {num} email in batch")
    print("="*60)

    if not to_email:
        to_email = input("Inserisci email di test: ").strip()

    # Crea lista di email di test
    emails = [
        (
            f"Test {i+1}/{num}",
            f"Questo è il test email #{i+1}\n\nSe ricevi questo, il rate limiting funziona!",
            "noreply@ainaudi.it",
            [to_email],
        )
        for i in range(num)
    ]

    sender = EmailSender(verbose=True)
    sent, failed = sender.send_batch(emails, batch_size=5)

    if failed == 0:
        print(f"✅ Tutti gli invii hanno successo!")
    else:
        print(f"⚠️  {failed} email non inviate")

    return sent, failed


def test_with_template(num: int = 5, to_email: str = None):
    """Testa l'invio con template Django."""
    print(f"\n🧪 TEST: Invio {num} email con template")
    print("="*60)

    if not to_email:
        to_email = input("Inserisci email di test: ").strip()

    # Esempio: se hai un template 'email/test.html'
    # render_to_string('email/test.html', {'user': 'Test User'})

    emails = [
        (
            f"Test Template {i+1}/{num}",
            f"Email con template #{i+1}",
            "noreply@ainaudi.it",
            [to_email],
        )
        for i in range(num)
    ]

    sender = EmailSender(verbose=True)
    sent, failed = sender.send_batch(emails, batch_size=5)

    return sent, failed


def main():
    parser = argparse.ArgumentParser(description='Test email sending with SES rate limiting')
    parser.add_argument('--mode', choices=['single', 'batch', 'template'], default='batch',
                        help='Mode: single (1 email), batch (N email), template (N email con template)')
    parser.add_argument('--num', type=int, default=5,
                        help='Numero di email da inviare (default: 5)')
    parser.add_argument('--to', dest='to_email', default=None,
                        help='Email di destinazione (default: prompt)')

    args = parser.parse_args()

    print(f"\n📧 AINAUDI Email Test")
    print(f"{'='*60}")
    print(f"AWS SES Rate Limit: {EmailSender.SES_RATE_LIMIT} email/sec")
    print(f"Delay tra email: {EmailSender.DELAY_BETWEEN_EMAILS*1000:.0f}ms")
    print(f"{'='*60}\n")

    if args.mode == 'single':
        test_single_email(args.to_email)
    elif args.mode == 'batch':
        test_batch_emails(args.num, args.to_email)
    elif args.mode == 'template':
        test_with_template(args.num, args.to_email)


if __name__ == '__main__':
    main()
