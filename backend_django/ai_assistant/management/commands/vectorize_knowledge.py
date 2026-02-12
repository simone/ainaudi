"""
Django management command to vectorize FAQ and Documento knowledge base.

Usage:
    python manage.py vectorize_knowledge                # All FAQs + Docs
    python manage.py vectorize_knowledge --faq-only     # Only FAQs
    python manage.py vectorize_knowledge --docs-only    # Only Docs
    python manage.py vectorize_knowledge --force        # Re-vectorize all (even if exists)
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from resources.models import FAQ, Documento
from ai_assistant.models import KnowledgeSource
import time


class Command(BaseCommand):
    help = 'Vectorize FAQ and Documento for AI Assistant RAG'

    def add_arguments(self, parser):
        parser.add_argument(
            '--faq-only',
            action='store_true',
            help='Vectorize only FAQs',
        )
        parser.add_argument(
            '--docs-only',
            action='store_true',
            help='Vectorize only Documenti',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-vectorize all (delete existing embeddings first)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        start_time = time.time()

        faq_only = options['faq_only']
        docs_only = options['docs_only']
        force = options['force']
        dry_run = options['dry_run']

        # Validation
        if faq_only and docs_only:
            raise CommandError('Cannot use --faq-only and --docs-only together')

        # Header
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('  🧠 AI Knowledge Base Vectorization'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN MODE - No changes will be made\n'))

        # Statistics
        stats = {
            'faq_processed': 0,
            'faq_created': 0,
            'faq_updated': 0,
            'faq_errors': 0,
            'doc_processed': 0,
            'doc_created': 0,
            'doc_updated': 0,
            'doc_errors': 0,
        }

        # Force delete existing embeddings
        if force and not dry_run:
            self.stdout.write('\n🗑️  Deleting existing KnowledgeSource...')
            deleted_count = KnowledgeSource.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f'   Deleted {deleted_count} embeddings\n'))

        # Process FAQs
        if not docs_only:
            self.stdout.write('\n📚 Processing FAQs...')
            self.stdout.write('-' * 70)
            stats.update(self._process_faqs(dry_run))

        # Process Documenti
        if not faq_only:
            self.stdout.write('\n📄 Processing Documenti...')
            self.stdout.write('-' * 70)
            stats.update(self._process_docs(dry_run))

        # Summary
        elapsed = time.time() - start_time
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('  ✅ Vectorization Complete!'))
        self.stdout.write('=' * 70)

        self.stdout.write(f'\n📊 Statistics:')
        self.stdout.write(f'   FAQs:')
        self.stdout.write(f'     - Processed: {stats["faq_processed"]}')
        self.stdout.write(f'     - Created:   {stats["faq_created"]}')
        self.stdout.write(f'     - Updated:   {stats["faq_updated"]}')
        if stats['faq_errors']:
            self.stdout.write(self.style.ERROR(f'     - Errors:    {stats["faq_errors"]}'))

        self.stdout.write(f'\n   Documenti:')
        self.stdout.write(f'     - Processed: {stats["doc_processed"]}')
        self.stdout.write(f'     - Created:   {stats["doc_created"]}')
        self.stdout.write(f'     - Updated:   {stats["doc_updated"]}')
        if stats['doc_errors']:
            self.stdout.write(self.style.ERROR(f'     - Errors:    {stats["doc_errors"]}'))

        total_created = stats['faq_created'] + stats['doc_created']
        total_updated = stats['faq_updated'] + stats['doc_updated']
        total_errors = stats['faq_errors'] + stats['doc_errors']

        self.stdout.write(f'\n   Total:')
        self.stdout.write(self.style.SUCCESS(f'     - Created:   {total_created}'))
        self.stdout.write(self.style.SUCCESS(f'     - Updated:   {total_updated}'))
        if total_errors:
            self.stdout.write(self.style.ERROR(f'     - Errors:    {total_errors}'))

        self.stdout.write(f'\n⏱️  Time elapsed: {elapsed:.1f}s\n')

    def _process_faqs(self, dry_run):
        """Process all active FAQs."""
        stats = {
            'faq_processed': 0,
            'faq_created': 0,
            'faq_updated': 0,
            'faq_errors': 0,
        }

        faqs = FAQ.objects.filter(is_attivo=True)
        total = faqs.count()

        if total == 0:
            self.stdout.write(self.style.WARNING('   No active FAQs found'))
            return stats

        for i, faq in enumerate(faqs, 1):
            try:
                if dry_run:
                    self.stdout.write(
                        f'   [{i}/{total}] Would process: {faq.domanda[:50]}...'
                    )
                else:
                    # Check if already exists
                    title = f"FAQ: {faq.domanda[:100]}"
                    existing = KnowledgeSource.objects.filter(title=title).exists()

                    # Trigger signal by saving
                    faq.save()

                    stats['faq_processed'] += 1
                    if existing:
                        stats['faq_updated'] += 1
                        action = 'Updated'
                        style = self.style.SUCCESS
                    else:
                        stats['faq_created'] += 1
                        action = 'Created'
                        style = self.style.SUCCESS

                    self.stdout.write(
                        style(f'   ✅ [{i}/{total}] {action}: {faq.domanda[:50]}...')
                    )
            except Exception as e:
                stats['faq_errors'] += 1
                self.stdout.write(
                    self.style.ERROR(f'   ❌ [{i}/{total}] Error: {faq.domanda[:50]}... - {str(e)[:50]}')
                )

        return stats

    def _process_docs(self, dry_run):
        """Process all active Documenti."""
        stats = {
            'doc_processed': 0,
            'doc_created': 0,
            'doc_updated': 0,
            'doc_errors': 0,
        }

        docs = Documento.objects.filter(is_attivo=True)
        total = docs.count()

        if total == 0:
            self.stdout.write(self.style.WARNING('   No active Documenti found'))
            return stats

        for i, doc in enumerate(docs, 1):
            try:
                if dry_run:
                    self.stdout.write(
                        f'   [{i}/{total}] Would process: {doc.titolo[:50]}...'
                    )
                else:
                    # Check if already exists
                    title = f"Doc: {doc.titolo[:100]}"
                    existing = KnowledgeSource.objects.filter(title=title).exists()

                    # Trigger signal by saving
                    doc.save()

                    stats['doc_processed'] += 1
                    if existing:
                        stats['doc_updated'] += 1
                        action = 'Updated'
                        style = self.style.SUCCESS
                    else:
                        stats['doc_created'] += 1
                        action = 'Created'
                        style = self.style.SUCCESS

                    self.stdout.write(
                        style(f'   ✅ [{i}/{total}] {action}: {doc.titolo[:50]}...')
                    )
            except Exception as e:
                stats['doc_errors'] += 1
                self.stdout.write(
                    self.style.ERROR(f'   ❌ [{i}/{total}] Error: {doc.titolo[:50]}... - {str(e)[:50]}')
                )

        return stats
