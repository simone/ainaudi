"""
Management command to ingest the user manual into the RAG knowledge base.

Usage:
    python manage.py ingest_manual
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from ai_assistant.models import KnowledgeSource
from ai_assistant.vertex_service import vertex_ai_service
import os


class Command(BaseCommand):
    help = 'Ingest user manual (MANUALE_RDL.md) into RAG knowledge base'

    def handle(self, *args, **options):
        # Path to manual (copied to backend_django for Docker access)
        manual_path = os.path.join(settings.BASE_DIR, 'MANUALE_RDL.md')

        if not os.path.exists(manual_path):
            self.stdout.write(self.style.ERROR(f'Manual not found at: {manual_path}'))
            self.stdout.write(self.style.WARNING('Make sure MANUALE_RDL.md is in backend_django/ directory'))
            return

        self.stdout.write(self.style.WARNING('Reading manual...'))

        try:
            # Read manual content
            with open(manual_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.stdout.write(self.style.SUCCESS(f'✓ Read {len(content)} characters'))

            # Generate embedding
            self.stdout.write(self.style.WARNING('Generating embedding with Vertex AI...'))
            embedding = vertex_ai_service.generate_embedding(content)
            self.stdout.write(self.style.SUCCESS(f'✓ Generated {len(embedding)}-dimensional embedding'))

            # Create or update KnowledgeSource
            ks, created = KnowledgeSource.objects.update_or_create(
                title='Manuale Utente AInaudi',
                source_type='MANUAL',
                defaults={
                    'content': content,
                    'embedding': embedding,
                    'is_active': True,
                }
            )

            action = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'\n✓ {action} KnowledgeSource (ID: {ks.id})'))
            self.stdout.write(self.style.SUCCESS('✓ Manual successfully ingested into RAG knowledge base'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {e}'))
            raise
