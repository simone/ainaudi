"""
Management command to update the 'sopra_15000_abitanti' flag for comuni
based on the number of registered voters (n_elettori) in their sections.

This flag is important for determining the electoral system:
- > 15,000: doppio turno (ballottaggio)
- ≤ 15,000: turno unico

Usage:
    python manage.py update_comuni_popolazione
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum, Count
from territory.models import Comune, SezioneElettorale


class Command(BaseCommand):
    help = 'Update sopra_15000_abitanti flag based on registered voters'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating'
        )
        parser.add_argument(
            '--threshold',
            type=int,
            default=15000,
            help='Population threshold (default: 15000)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        threshold = options['threshold']

        self.stdout.write(f'Analyzing comuni with threshold: {threshold:,} inhabitants')
        self.stdout.write('')

        # Check if sections have n_elettori data
        sections_with_data = SezioneElettorale.objects.filter(
            n_elettori__isnull=False,
            n_elettori__gt=0
        ).count()

        use_estimate = sections_with_data == 0

        if use_estimate:
            self.stdout.write(
                self.style.WARNING(
                    'No n_elettori data in sections. Using estimate: n_sezioni × 800'
                )
            )
            self.stdout.write('')

        # Get all comuni with their total voters or section count
        comuni_stats = Comune.objects.annotate(
            totale_elettori=Sum('sezioni__n_elettori'),
            n_sezioni=Count('sezioni')
        ).filter(n_sezioni__gt=0).order_by('-n_sezioni')

        updated_sopra = 0
        updated_sotto = 0
        no_data = 0

        for comune in comuni_stats:
            # Calculate estimated voters
            if use_estimate:
                # Estimate: avg 800 voters per section
                stima_elettori = comune.n_sezioni * 800
            else:
                stima_elettori = comune.totale_elettori or 0

            if stima_elettori == 0:
                no_data += 1
                continue

            # Determine if above threshold
            sopra = stima_elettori > threshold

            # Check if needs update
            if comune.sopra_15000_abitanti != sopra:
                if dry_run:
                    status = "SOPRA" if sopra else "SOTTO"
                    elettori_str = f"~{stima_elettori:,}" if use_estimate else f"{stima_elettori:,}"
                    self.stdout.write(
                        f'{comune.nome} ({comune.provincia.sigla}): '
                        f'{elettori_str} elettori → {status} 15k'
                    )
                else:
                    comune.sopra_15000_abitanti = sopra
                    comune.save(update_fields=['sopra_15000_abitanti'])

                if sopra:
                    updated_sopra += 1
                else:
                    updated_sotto += 1

        # Summary
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.SUCCESS('DRY RUN - no changes made'))
        else:
            self.stdout.write(self.style.SUCCESS('Update complete:'))

        self.stdout.write(f'  Updated to SOPRA 15k: {updated_sopra}')
        self.stdout.write(f'  Updated to SOTTO 15k: {updated_sotto}')
        self.stdout.write(f'  No data (skipped): {no_data}')
        self.stdout.write('')

        # Show top 20 comuni by population
        if not dry_run:
            label = 'elettori stimati' if use_estimate else 'elettori iscritti'
            self.stdout.write(f'Top 20 comuni per {label}:')
            self.stdout.write('-' * 60)

            top_comuni = Comune.objects.annotate(
                totale_elettori=Sum('sezioni__n_elettori'),
                n_sezioni=Count('sezioni')
            ).filter(
                n_sezioni__gt=0
            ).order_by('-n_sezioni')[:20]

            for i, comune in enumerate(top_comuni, 1):
                if use_estimate:
                    elettori = comune.n_sezioni * 800
                    elettori_str = f"~{elettori:>8,}"
                else:
                    elettori = comune.totale_elettori or 0
                    elettori_str = f"{elettori:>8,}"

                flag = "🔴 SOPRA" if comune.sopra_15000_abitanti else "🟢 SOTTO"
                self.stdout.write(
                    f'{i:2d}. {comune.nome:20s} ({comune.provincia.sigla}): '
                    f'{elettori_str} elettori {flag}'
                )
