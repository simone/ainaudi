#!/usr/bin/env python
"""
Script di test per l'invio email RDL (SOLO LOG, nessun invio reale)

Usage:
    docker-compose exec backend python test_email_rdl.py <processo_id>

Example:
    docker-compose exec backend python test_email_rdl.py 1
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from delegations.models import ProcessoDesignazione
from delegations.services import RDLEmailService


def test_email_processo(processo_id):
    """Test invio email per un processo."""
    try:
        processo = ProcessoDesignazione.objects.get(id=processo_id)

        print(f"\n{'='*80}")
        print(f"🧪 TEST INVIO EMAIL - Processo #{processo.id}")
        print(f"{'='*80}")
        print(f"Consultazione: {processo.consultazione.nome}")
        print(f"Stato: {processo.stato}")
        print(f"N. Designazioni: {processo.n_designazioni}")
        print(f"{'='*80}\n")

        if processo.stato != 'APPROVATO':
            print(f"⚠️  ATTENZIONE: Processo non in stato APPROVATO (stato attuale: {processo.stato})")
            risposta = input("Vuoi continuare comunque? (y/n): ")
            if risposta.lower() != 'y':
                print("❌ Test annullato")
                return

        # Avvia invio asincrono
        print("🚀 Avvio invio email asincrono...")
        task_id = RDLEmailService.invia_notifiche_processo_async(
            processo=processo,
            user_email='test@example.com'
        )

        print(f"✅ Task avviato: {task_id}")
        print("\n📊 Monitoraggio progress...")

        import time
        while True:
            time.sleep(2)
            progress = RDLEmailService.get_task_progress(task_id)

            if progress['status'] == 'NOT_FOUND':
                print("❌ Task non trovato")
                break

            status = progress['status']
            current = progress.get('current', 0)
            total = progress.get('total', 0)
            sent = progress.get('sent', 0)
            failed = progress.get('failed', 0)

            print(f"Status: {status} | Progress: {current}/{total} | Sent: {sent} | Failed: {failed}")

            if status == 'SUCCESS':
                print(f"\n✅ Invio completato!")
                print(f"📧 Email inviate: {sent}")
                print(f"❌ Email fallite: {failed}")
                break
            elif status == 'FAILURE':
                print(f"\n❌ Invio fallito: {progress.get('error', 'Errore sconosciuto')}")
                break

        print(f"\n{'='*80}")
        print("✅ Test completato")
        print(f"{'='*80}\n")

        # Verifica logs nel database
        logs = processo.email_logs.all().order_by('-sent_at')[:10]
        if logs:
            print("\n📋 Ultimi 10 log email:")
            for log in logs:
                icon = '✅' if log.stato == 'SUCCESS' else '❌'
                print(f"  {icon} {log.destinatario_email} ({log.tipo_rdl}) - {log.sent_at.strftime('%H:%M:%S')}")

    except ProcessoDesignazione.DoesNotExist:
        print(f"❌ Processo #{processo_id} non trovato")
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_email_rdl.py <processo_id>")
        print("\nProcessi disponibili:")
        from delegations.models import ProcessoDesignazione
        processi = ProcessoDesignazione.objects.filter(stato='APPROVATO').order_by('-id')[:5]
        if processi:
            for p in processi:
                print(f"  - Processo #{p.id}: {p.consultazione.nome} ({p.n_designazioni} sezioni)")
        else:
            print("  Nessun processo APPROVATO trovato")
        sys.exit(1)

    processo_id = int(sys.argv[1])
    test_email_processo(processo_id)
