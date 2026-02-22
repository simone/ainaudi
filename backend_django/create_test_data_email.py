#!/usr/bin/env python
"""
Crea dati di test per verificare invio email RDL.

Crea:
- 1 Processo in stato APPROVATO
- 10 Designazioni CONFERMATE con RDL (5 con doppio ruolo)
- Email di test per verificare raggruppamento

Usage:
    docker-compose exec backend python create_test_data_email.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from delegations.models import ProcessoDesignazione, DesignazioneRDL, Delegato
from elections.models import ConsultazioneElettorale
from territory.models import SezioneElettorale, Comune
from documents.models import Template
from django.utils import timezone
from django.core.files.base import ContentFile


def create_test_data():
    print("\n" + "="*80)
    print("🧪 CREAZIONE DATI TEST EMAIL RDL")
    print("="*80 + "\n")

    # 1. Trova o crea consultazione
    consultazione, _ = ConsultazioneElettorale.objects.get_or_create(
        nome="Test Elezioni 2026",
        defaults={
            'data_inizio': timezone.now().date(),
            'data_fine': timezone.now().date(),
            'is_attiva': True
        }
    )
    print(f"✅ Consultazione: {consultazione.nome} (#{consultazione.id})")

    # 2. Trova comune (Roma o primo disponibile)
    comune = Comune.objects.filter(nome__icontains='roma').first()
    if not comune:
        comune = Comune.objects.first()

    if not comune:
        print("❌ Nessun comune trovato nel database")
        return

    print(f"✅ Comune: {comune.nome}")

    # 3. Trova o crea sezioni elettorali
    sezioni = list(SezioneElettorale.objects.filter(comune=comune)[:10])

    if len(sezioni) < 10:
        print(f"⚠️  Solo {len(sezioni)} sezioni disponibili (servono 10), creando...")
        for i in range(len(sezioni), 10):
            sezione = SezioneElettorale.objects.create(
                comune=comune,
                numero=str(1000 + i),
                indirizzo=f"Via Test {i}",
                denominazione=f"Seggio Test {i}"
            )
            sezioni.append(sezione)

    print(f"✅ Sezioni: {len(sezioni)} sezioni create/trovate")

    # 4. Trova o crea delegato
    delegato, _ = Delegato.objects.get_or_create(
        email='delegato.test@m5s.it',
        defaults={
            'nome': 'Mario',
            'cognome': 'Test',
            'consultazione': consultazione,
            'carica': 'Deputato',
            'data_nomina': timezone.now().date()
        }
    )
    print(f"✅ Delegato: {delegato.cognome} {delegato.nome}")

    # 5. Trova template (opzionale)
    template_ind = Template.objects.filter(template_type='DESIGNATION_SINGLE').first()
    template_cum = Template.objects.filter(template_type='DESIGNATION_MULTI').first()

    if template_ind and template_cum:
        print(f"✅ Template: {template_ind.name}, {template_cum.name}")
    else:
        print("⚠️  Template non trovati, creando processo senza PDF")
        template_ind = None
        template_cum = None

    # 6. Crea processo APPROVATO
    processo = ProcessoDesignazione.objects.create(
        consultazione=consultazione,
        comune=comune,
        delegato=delegato,
        template_individuale=template_ind,
        template_cumulativo=template_cum,
        stato='APPROVATO',
        created_by_email='admin@test.com',
        approvata_at=timezone.now(),
        approvata_da_email='admin@test.com',
        n_designazioni=10,
        dati_delegato={
            'nome': delegato.nome,
            'cognome': delegato.cognome,
            'email': delegato.email
        }
    )

    # Crea PDF fittizio per evitare errori
    if template_ind:
        processo.documento_individuale.save(
            f'test_processo_{processo.id}_individuale.pdf',
            ContentFile(b'%PDF-1.4 fake pdf for testing'),
            save=False
        )
    if template_cum:
        processo.documento_cumulativo.save(
            f'test_processo_{processo.id}_cumulativo.pdf',
            ContentFile(b'%PDF-1.4 fake pdf for testing'),
            save=False
        )

    processo.save()

    print(f"✅ Processo #{processo.id} creato in stato APPROVATO")

    # 7. Crea designazioni con RDL di test
    # Creiamo 5 RDL con doppio ruolo (effettivo + supplente)
    # e 5 RDL con ruolo singolo
    rdl_data = [
        # Doppio ruolo (stessa email per effettivo e supplente in sezioni diverse)
        {'eff_email': 'rdl1@test.com', 'eff_nome': 'Mario', 'eff_cognome': 'Rossi', 'sup_email': 'rdl11@test.com', 'sup_nome': 'Laura', 'sup_cognome': 'Bianchi'},
        {'eff_email': 'rdl2@test.com', 'eff_nome': 'Luigi', 'eff_cognome': 'Verdi', 'sup_email': 'rdl1@test.com', 'sup_nome': 'Mario', 'sup_cognome': 'Rossi'},  # rdl1 anche supplente!
        {'eff_email': 'rdl3@test.com', 'eff_nome': 'Giovanni', 'eff_cognome': 'Neri', 'sup_email': 'rdl2@test.com', 'sup_nome': 'Luigi', 'sup_cognome': 'Verdi'},  # rdl2 anche supplente!
        {'eff_email': 'rdl4@test.com', 'eff_nome': 'Paolo', 'eff_cognome': 'Gialli', 'sup_email': 'rdl12@test.com', 'sup_nome': 'Sara', 'sup_cognome': 'Blu'},
        {'eff_email': 'rdl5@test.com', 'eff_nome': 'Marco', 'eff_cognome': 'Viola', 'sup_email': 'rdl3@test.com', 'sup_nome': 'Giovanni', 'sup_cognome': 'Neri'},  # rdl3 anche supplente!
        # Ruolo singolo
        {'eff_email': 'rdl6@test.com', 'eff_nome': 'Andrea', 'eff_cognome': 'Rosa', 'sup_email': 'rdl13@test.com', 'sup_nome': 'Elena', 'sup_cognome': 'Arancio'},
        {'eff_email': 'rdl7@test.com', 'eff_nome': 'Luca', 'eff_cognome': 'Grigio', 'sup_email': 'rdl14@test.com', 'sup_nome': 'Chiara', 'sup_cognome': 'Marrone'},
        {'eff_email': 'rdl8@test.com', 'eff_nome': 'Simone', 'eff_cognome': 'Celeste', 'sup_email': 'rdl15@test.com', 'sup_nome': 'Giulia', 'sup_cognome': 'Verde'},
        {'eff_email': 'rdl9@test.com', 'eff_nome': 'Matteo', 'eff_cognome': 'Bianco', 'sup_email': 'rdl16@test.com', 'sup_nome': 'Francesca', 'sup_cognome': 'Nero'},
        {'eff_email': 'rdl10@test.com', 'eff_nome': 'Davide', 'eff_cognome': 'Rosso', 'sup_email': 'rdl17@test.com', 'sup_nome': 'Martina', 'sup_cognome': 'Giallo'},
    ]

    email_uniche = set()
    for i, (sezione, rdl) in enumerate(zip(sezioni, rdl_data)):
        des = DesignazioneRDL.objects.create(
            processo=processo,
            sezione=sezione,
            delegato=delegato,
            stato='CONFERMATA',
            is_attiva=True,
            # Effettivo
            effettivo_email=rdl['eff_email'],
            effettivo_nome=rdl['eff_nome'],
            effettivo_cognome=rdl['eff_cognome'],
            effettivo_data_nascita='1980-01-01',
            effettivo_luogo_nascita='Roma',
            effettivo_domicilio='Via Test 1',
            # Supplente
            supplente_email=rdl['sup_email'],
            supplente_nome=rdl['sup_nome'],
            supplente_cognome=rdl['sup_cognome'],
            supplente_data_nascita='1985-01-01',
            supplente_luogo_nascita='Roma',
            supplente_domicilio='Via Test 2',
            # Metadata
            data_designazione=timezone.now(),
            approvata_da_email='admin@test.com',
            data_approvazione=timezone.now()
        )
        email_uniche.add(rdl['eff_email'])
        email_uniche.add(rdl['sup_email'])
        print(f"  ✅ Designazione {i+1}: Sez.{sezione.numero} - Eff: {rdl['eff_email']}, Sup: {rdl['sup_email']}")

    print(f"\n✅ {len(sezioni)} designazioni create")
    print(f"✅ {len(email_uniche)} email uniche (alcuni RDL hanno doppio ruolo!)")

    print("\n" + "="*80)
    print("✅ DATI TEST CREATI CON SUCCESSO")
    print("="*80)
    print(f"\n🚀 Ora puoi testare con:")
    print(f"   docker-compose exec backend python test_email_rdl.py {processo.id}")
    print(f"\nOppure dall'interfaccia web:")
    print(f"   http://localhost:3000 → Gestione Designazioni → Processo #{processo.id}\n")

    return processo


if __name__ == '__main__':
    try:
        processo = create_test_data()
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        import traceback
        traceback.print_exc()
