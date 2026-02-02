#!/usr/bin/env python
"""
Script per caricare la consultazione multipla 17 Giugno 2025.

Uso:
    cd backend_django
    python manage.py shell < fixtures/load_consultazione_multipla.py

Oppure:
    python manage.py loaddata fixtures/consultazione_multipla_2025.json
    python manage.py shell < fixtures/load_consultazione_multipla.py
"""
import json
from django.core.management import call_command
from elections.models import ConsultazioneElettorale, TipoElezione, SchedaElettorale
from territorio.models import Comune, Regione

# Prima carica la fixture base
print("Caricamento fixture base...")
call_command('loaddata', 'fixtures/consultazione_multipla_2025.json')

# Trova la consultazione
consultazione = ConsultazioneElettorale.objects.get(pk=2)
print(f"Consultazione: {consultazione.nome}")

# Trova il tipo elezione COMUNALI
tipo_comunali = TipoElezione.objects.get(consultazione=consultazione, tipo='COMUNALI')

# Aggiungi comuni che votano per le comunali (esempi da varie regioni)
comuni_votanti = [
    # Lazio
    'Viterbo',
    'Latina',
    'Frosinone',
    # Lombardia
    'Bergamo',
    'Brescia',
    'Varese',
    # Campania
    'Caserta',
    'Avellino',
    # Emilia-Romagna
    'Ravenna',
    'Rimini',
    # Piemonte
    'Novara',
    'Alessandria',
    # Toscana
    'Arezzo',
    'Prato',
    # Puglia
    'Lecce',
    'Taranto',
    # Sicilia
    'Ragusa',
    'Trapani',
    # Veneto
    'Vicenza',
    'Treviso',
]

print(f"\nAggiunta comuni alle elezioni comunali...")
comuni_aggiunti = 0
for nome_comune in comuni_votanti:
    try:
        comune = Comune.objects.get(nome__iexact=nome_comune)
        tipo_comunali.comuni.add(comune)
        comuni_aggiunti += 1
        print(f"  + {comune.nome} ({comune.provincia.nome})")
    except Comune.DoesNotExist:
        print(f"  ! Comune non trovato: {nome_comune}")
    except Comune.MultipleObjectsReturned:
        # Prendi il primo (capoluogo di provincia)
        comune = Comune.objects.filter(nome__iexact=nome_comune).first()
        tipo_comunali.comuni.add(comune)
        comuni_aggiunti += 1
        print(f"  + {comune.nome} ({comune.provincia.nome}) [primo match]")

print(f"\nComuni aggiunti: {comuni_aggiunti}")

# Riepilogo
print("\n" + "="*60)
print(f"CONSULTAZIONE: {consultazione.nome}")
print(f"Date: {consultazione.data_inizio} - {consultazione.data_fine}")
print("="*60)

print("\nTIPI DI ELEZIONE:")
for tipo in consultazione.tipi_elezione.all():
    print(f"\n  {tipo.get_tipo_display()}")
    if tipo.tipo == 'COMUNALI':
        print(f"    Comuni votanti: {tipo.comuni.count()}")
        for comune in tipo.comuni.all()[:5]:
            print(f"      - {comune.nome} ({comune.provincia.regione.nome})")
        if tipo.comuni.count() > 5:
            print(f"      ... e altri {tipo.comuni.count() - 5}")

    print(f"    Schede:")
    for scheda in tipo.schede.all():
        print(f"      - {scheda.nome} ({scheda.colore})")

print("\n" + "="*60)
print("Fixture caricata con successo!")
print("="*60)
