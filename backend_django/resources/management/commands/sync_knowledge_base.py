"""
Management command to sync all Documenti and FAQ into KnowledgeSource.

Usage:
    python manage.py sync_knowledge_base
    python manage.py sync_knowledge_base --clear  # Clear existing first
"""
from django.core.management.base import BaseCommand
from resources.models import Documento, FAQ


class Command(BaseCommand):
    help = 'Sync all Documenti and FAQ to KnowledgeSource (triggers signals)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all KnowledgeSource entries before syncing',
        )

    def handle(self, *args, **options):
        try:
            from ai_assistant.models import KnowledgeSource
        except ImportError:
            self.stdout.write(self.style.ERROR('ai_assistant app not installed'))
            return

        # Clear existing if requested
        if options['clear']:
            count = KnowledgeSource.objects.count()
            KnowledgeSource.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {count} existing KnowledgeSource entries'))

        # Sync Documenti (triggers post_save signal)
        documenti = Documento.objects.filter(is_attivo=True)
        self.stdout.write(f'Syncing {documenti.count()} Documenti...')

        synced_docs = 0
        failed_docs = 0
        for doc in documenti:
            try:
                # Re-save triggers the signal
                doc.save()
                synced_docs += 1
                if synced_docs % 10 == 0:
                    self.stdout.write(f'  Processed {synced_docs} documents...')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Failed to sync Documento {doc.id}: {e}'))
                failed_docs += 1

        self.stdout.write(self.style.SUCCESS(f'✓ Synced {synced_docs} Documenti ({failed_docs} failed)'))

        # Sync FAQ (triggers post_save signal)
        faqs = FAQ.objects.filter(is_attivo=True)
        self.stdout.write(f'Syncing {faqs.count()} FAQ...')

        synced_faqs = 0
        failed_faqs = 0
        for faq in faqs:
            try:
                # Re-save triggers the signal
                faq.save()
                synced_faqs += 1
                if synced_faqs % 10 == 0:
                    self.stdout.write(f'  Processed {synced_faqs} FAQs...')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Failed to sync FAQ {faq.id}: {e}'))
                failed_faqs += 1

        self.stdout.write(self.style.SUCCESS(f'✓ Synced {synced_faqs} FAQ ({failed_faqs} failed)'))

        # Summary
        total_ks = KnowledgeSource.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n✓ Done! Total KnowledgeSource entries: {total_ks}'))
