"""
Management command per creare delegati della provincia di Roma con comuni specifici.
Script idempotente: può essere eseguito più volte senza problemi.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from delegations.models import Delegato
from elections.models import ConsultazioneElettorale
from territory.models import Comune


DELEGATI = [
    {
        "nome": "Franca",
        "cognome": "Della Croce",
        "email": "francadellacroce@hotmail.it",
        "comuni": ["Nettuno"],
    },
    {
        "nome": "Ada",
        "cognome": "Santamaita",
        "email": "ada.santamaita@gmail.com",
        "comuni": ["Marino"],
    },
    {
        "nome": "Nando",
        "cognome": "Vittori",
        "email": "n.vittori63@gmail.com",
        "comuni": ["Colleferro", "Segni", "Artena", "Valmontone", "Carpineto Romano"],
    },
    {
        "nome": "Piero",
        "cognome": "Famiglietti",
        "email": "pierofamiglietti@tiscali.it",
        "comuni": ["Monte Compatri", "Rocca Priora", "Monte Porzio Catone", "Grottaferrata", "Frascati"],
    },
    {
        "nome": "Walter",
        "cognome": "Ippolito",
        "email": "walterippolito73@gmail.com",
        "comuni": ["Genzano di Roma", "Velletri", "Lariano", "Lanuvio", "Nemi"],
    },
    {
        "nome": "Marco",
        "cognome": "Galderesi",
        "email": "marco.galderesi@gmail.com",
        "comuni": ["Anzio"],
    },
    {
        "nome": "Nadia",
        "cognome": "Damato",
        "email": "damato6713@gmail.com",
        "comuni": ["Pomezia"],
    },
    {
        "nome": "Karim",
        "cognome": "Thib",
        "email": "karim.thib93@gmail.com",
        "comuni": ["Albano Laziale", "Ariccia", "Castel Gandolfo", "Monte Compatri"],
    },
    {
        "nome": "Beatrice",
        "cognome": "Piras",
        "email": "beacasale1@gmail.com",
        "comuni": ["Ardea"],
    },
]


class Command(BaseCommand):
    help = 'Crea delegati della provincia di Roma con comuni specifici'

    def add_arguments(self, parser):
        parser.add_argument(
            '--consultazione',
            type=int,
            default=None,
            help='ID della consultazione elettorale (default: consultazione attiva)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra cosa verrebbe fatto senza eseguire modifiche'
        )

    def handle(self, *args, **options):
        consultazione_id = options['consultazione']
        dry_run = options['dry_run']

        try:
            if consultazione_id is None:
                consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
                if not consultazione:
                    raise CommandError("Nessuna consultazione attiva trovata. Specifica --consultazione ID")
            else:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)

            self.stdout.write(f"Consultazione: {consultazione.nome} (ID: {consultazione.id})")

            if dry_run:
                self.stdout.write(self.style.WARNING("\n--- DRY RUN ---\n"))

            with transaction.atomic():
                for data in DELEGATI:
                    comuni_trovati = []
                    comuni_mancanti = []
                    for nome_comune in data['comuni']:
                        comune = Comune.objects.filter(nome__iexact=nome_comune).first()
                        if comune:
                            comuni_trovati.append(comune)
                        else:
                            comuni_mancanti.append(nome_comune)

                    if comuni_mancanti:
                        self.stdout.write(self.style.ERROR(
                            f"  ERRORE: Comuni non trovati per {data['nome']} {data['cognome']}: {', '.join(comuni_mancanti)}"
                        ))
                        continue

                    if dry_run:
                        self.stdout.write(
                            f"  [DRY] {data['nome']} {data['cognome']} ({data['email']})"
                            f" - Comuni: {', '.join(c.nome for c in comuni_trovati)}"
                        )
                        continue

                    delegato, created = Delegato.objects.get_or_create(
                        consultazione=consultazione,
                        cognome=data['cognome'],
                        nome=data['nome'],
                        defaults={
                            'email': data['email'],
                            'carica': 'RAPPRESENTANTE_PARTITO',
                            'data_nomina': '2026-03-14',
                        }
                    )

                    if not created:
                        delegato.email = data['email']
                        delegato.save()

                    delegato.comuni.set(comuni_trovati)

                    status = "Creato" if created else "Aggiornato"
                    self.stdout.write(self.style.SUCCESS(
                        f"  {status}: {data['nome']} {data['cognome']}"
                        f" - {len(comuni_trovati)} comuni"
                    ))

                if dry_run:
                    raise CommandError("Dry run completato, nessuna modifica effettuata.")

            self.stdout.write(self.style.SUCCESS(
                f"\nCompletato! {len(DELEGATI)} delegati configurati."
            ))

        except ConsultazioneElettorale.DoesNotExist:
            raise CommandError(f"Consultazione con ID {consultazione_id} non trovata")
