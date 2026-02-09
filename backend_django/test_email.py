#!/usr/bin/env python
"""
Script per testare invio email con SendGrid
Uso: python test_email.py destinatario@example.com
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings


def test_email(to_email):
    """Invia email di test"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Test Invio Email - SendGrid")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    print(f"📧 Configurazione EMAIL:")
    print(f"   Backend: {settings.EMAIL_BACKEND}")
    print(f"   Host: {settings.EMAIL_HOST}")
    print(f"   Port: {settings.EMAIL_PORT}")
    print(f"   TLS: {settings.EMAIL_USE_TLS}")
    print(f"   User: {settings.EMAIL_HOST_USER}")
    print(f"   From: {settings.DEFAULT_FROM_EMAIL}")
    print()
    print(f"📨 Invio email di test a: {to_email}")
    print()

    try:
        send_mail(
            subject='[AInaudi] Test Email - SendGrid',
            message='Questo è un messaggio di test da AInaudi.\n\nSe ricevi questa email, la configurazione SendGrid funziona correttamente! ✅',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        print("✅ Email inviata con successo!")
        print()
        print("📬 Controlla la casella di posta di:", to_email)
        print("   (Controlla anche spam/promozioni)")
        print()

    except Exception as e:
        print("❌ Errore invio email:")
        print(f"   {type(e).__name__}: {e}")
        print()
        print("🔍 Possibili cause:")
        print("   - SendGrid API Key non valida")
        print("   - EMAIL_HOST_PASSWORD non configurato")
        print("   - Sender email non verificato su SendGrid")
        print("   - Firewall blocca porta 587")
        print()
        return False

    return True


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python test_email.py destinatario@example.com")
        sys.exit(1)

    to_email = sys.argv[1]

    # Valida formato email
    if '@' not in to_email:
        print("❌ Email non valida:", to_email)
        sys.exit(1)

    success = test_email(to_email)
    sys.exit(0 if success else 1)
