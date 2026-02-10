"""
Management command per creare delegati per la provincia di Roma (escluso Roma Capitale).
Script idempotente: può essere eseguito più volte senza problemi.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from delegations.models import Delegato
from elections.models import ConsultazioneElettorale
from territory.models import Comune, Provincia


class Command(BaseCommand):
    help = 'Crea delegati per tutti i comuni della provincia di Roma (escluso Roma Capitale)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--consultazione',
            type=int,
            default=None,
            help='ID della consultazione elettorale (default: consultazione attiva)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forza la ricreazione dei delegati anche se esistono già'
        )

    def handle(self, *args, **options):
        consultazione_id = options['consultazione']
        force = options['force']

        # Dati dei delegati
        delegati_data = [
            {
                "cognome": "Lucernoni",
                "nome": "Daniela",
                "email": "dani.lucernoni@gmail.com",
                "telefono": "3285720419",
            },
            {
                "cognome": "Guain",
                "nome": "Alessio",
                "email": "alessio.guain@gmail.com",
                "telefono": "+39 329 413 2055",
            },
            {
                "cognome": "Carbonara",
                "nome": "Viviana",
                "email": "vivianacarbonara.76@gmail.com",
                "telefono": "+39 333 486 8734",
            },
        ]

        try:
            # Verifica consultazione
            if consultazione_id is None:
                # Usa la consultazione attiva
                consultazione = ConsultazioneElettorale.objects.filter(is_attiva=True).first()
                if not consultazione:
                    raise CommandError("Nessuna consultazione attiva trovata. Specifica --consultazione ID")
                self.stdout.write(f"Consultazione attiva: {consultazione.nome} (ID: {consultazione.id})")
            else:
                consultazione = ConsultazioneElettorale.objects.get(id=consultazione_id)
                self.stdout.write(f"Consultazione: {consultazione.nome}")

            # Get provincia di Roma
            provincia_roma = Provincia.objects.get(codice_istat='058')
            self.stdout.write(f"Provincia: {provincia_roma.nome}")

            # Get tutti i comuni escluso Roma Capitale
            comuni = Comune.objects.filter(
                provincia=provincia_roma
            ).exclude(
                codice_istat='058091'
            ).order_by('nome')

            self.stdout.write(
                self.style.SUCCESS(
                    f"Trovati {comuni.count()} comuni (Roma Capitale esclusa)"
                )
            )

            # Crea o aggiorna delegati
            with transaction.atomic():
                for delegato_data in delegati_data:
                    email = delegato_data['email']

                    # Check se esiste già
                    delegato, created = Delegato.objects.get_or_create(
                        consultazione=consultazione,
                        email=email,
                        defaults={
                            'cognome': delegato_data['cognome'],
                            'nome': delegato_data['nome'],
                            'telefono': delegato_data.get('telefono', ''),
                            'carica': 'RAPPRESENTANTE_PARTITO',
                            'data_nomina': '2026-02-10',
                        }
                    )

                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"✓ Creato delegato: {delegato.nome} {delegato.cognome}"
                            )
                        )
                    else:
                        if force:
                            # Aggiorna dati
                            delegato.cognome = delegato_data['cognome']
                            delegato.nome = delegato_data['nome']
                            delegato.telefono = delegato_data.get('telefono', '')
                            delegato.save()
                            self.stdout.write(
                                self.style.WARNING(
                                    f"⟳ Aggiornato delegato: {delegato.nome} {delegato.cognome}"
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"⊘ Delegato già esistente: {delegato.nome} {delegato.cognome}"
                                )
                            )

                    # Assegna comuni (sostituisce i precedenti)
                    delegato.comuni.set(comuni)

                    self.stdout.write(
                        f"  → Assegnati {comuni.count()} comuni a {delegato.nome} {delegato.cognome}"
                    )

                    # I RoleAssignment vengono creati automaticamente dai signals

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Completato! {len(delegati_data)} delegati configurati."
                )
            )
            self.stdout.write(
                "I RoleAssignment sono stati creati automaticamente dai signals."
            )

        except ConsultazioneElettorale.DoesNotExist:
            raise CommandError(
                f"Consultazione con ID {consultazione_id} non trovata"
            )
        except Provincia.DoesNotExist:
            raise CommandError("Provincia di Roma non trovata (codice ISTAT: 058)")
        except Exception as e:
            raise CommandError(f"Errore: {str(e)}")
