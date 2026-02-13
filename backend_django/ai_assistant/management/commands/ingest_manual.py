"""
Management command to ingest documents into the RAG knowledge base.

Supports: Markdown (.md) and PDF (.pdf) files, both local paths and URLs.

Usage:
    python manage.py ingest_manual                           # Default: MANUALE_RDL.md
    python manage.py ingest_manual --file path/to/doc.pdf
    python manage.py ingest_manual --file https://example.com/doc.pdf
    python manage.py ingest_manual --file doc.md --title "My Doc" --type PROCEDURE
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from ai_assistant.models import KnowledgeSource
from ai_assistant.extractors import PDFExtractor
from ai_assistant.vertex_service import vertex_ai_service
import os


# Max characters per chunk for embedding (text-embedding-004 supports ~8k tokens ≈ 20k chars)
CHUNK_MAX_CHARS = 15000


def chunk_text(text, max_chars=CHUNK_MAX_CHARS):
    """Split text into chunks, trying to break at paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    paragraphs = text.split('\n\n')
    current_chunk = ''

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # If a single paragraph exceeds max_chars, split it
            if len(para) > max_chars:
                for i in range(0, len(para), max_chars):
                    chunks.append(para[i:i + max_chars].strip())
                current_chunk = ''
            else:
                current_chunk = para
        else:
            current_chunk = current_chunk + '\n\n' + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def read_content(file_source):
    """Read content from a file path or URL. Returns (text, detected_extension)."""
    is_url = file_source.startswith('http')

    if is_url:
        ext = '.pdf' if file_source.lower().endswith('.pdf') else '.md'
    else:
        ext = os.path.splitext(file_source)[1].lower()

    if ext == '.pdf':
        text = PDFExtractor.extract_text(file_source)
        if not text:
            raise ValueError(f'Could not extract text from PDF: {file_source}')
        return text, ext

    # Default: read as text (markdown, txt, etc.)
    if is_url:
        import requests
        response = requests.get(file_source, timeout=30)
        response.raise_for_status()
        return response.text, ext

    with open(file_source, 'r', encoding='utf-8') as f:
        return f.read(), ext


class Command(BaseCommand):
    help = 'Ingest documents (MD/PDF, local/URL) into RAG knowledge base'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', '-f',
            type=str,
            default=None,
            help='File path or URL (default: MANUALE_RDL.md)'
        )
        parser.add_argument(
            '--title', '-t',
            type=str,
            default=None,
            help='Document title (default: filename)'
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['FAQ', 'PROCEDURE', 'SLIDE', 'MANUAL'],
            default='MANUAL',
            help='Source type (default: MANUAL)'
        )
        parser.add_argument(
            '--url',
            type=str,
            default='',
            help='Source URL for PDF preview links'
        )

    def handle(self, *args, **options):
        file_source = options['file']
        source_type = options['type']
        source_url = options['url'] or ''

        # Default: MANUALE_RDL.md
        if not file_source:
            file_source = os.path.join(settings.BASE_DIR, 'MANUALE_RDL.md')

        # Resolve relative paths
        if not file_source.startswith('http') and not os.path.isabs(file_source):
            file_source = os.path.join(settings.BASE_DIR, file_source)

        # Determine title
        if options['title']:
            title = options['title']
        elif file_source.startswith('http'):
            title = file_source.split('/')[-1].rsplit('.', 1)[0]
        else:
            title = os.path.basename(file_source).rsplit('.', 1)[0]

        # Check file exists (for local files)
        if not file_source.startswith('http') and not os.path.exists(file_source):
            self.stdout.write(self.style.ERROR(f'File not found: {file_source}'))
            return

        self.stdout.write(self.style.WARNING(f'Reading: {file_source}'))

        try:
            content, ext = read_content(file_source)
            self.stdout.write(self.style.SUCCESS(
                f'✓ Extracted {len(content)} characters from {ext} file'
            ))

            # Chunk if needed
            chunks = chunk_text(content)
            total_chunks = len(chunks)

            if total_chunks > 1:
                self.stdout.write(self.style.WARNING(
                    f'Document split into {total_chunks} chunks'
                ))

            # Delete existing entries for this title to avoid duplicates
            deleted, _ = KnowledgeSource.objects.filter(
                title__startswith=title,
                source_type=source_type,
            ).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(
                    f'Removed {deleted} existing entries for "{title}"'
                ))

            # Process each chunk
            for i, chunk in enumerate(chunks):
                chunk_title = title if total_chunks == 1 else f'{title} ({i + 1}/{total_chunks})'

                self.stdout.write(self.style.WARNING(
                    f'[{i + 1}/{total_chunks}] Generating embedding for "{chunk_title}" '
                    f'({len(chunk)} chars)...'
                ))

                embedding = vertex_ai_service.generate_embedding(chunk)

                KnowledgeSource.objects.create(
                    title=chunk_title,
                    source_type=source_type,
                    content=chunk,
                    embedding=embedding,
                    source_url=source_url,
                    is_active=True,
                )

                self.stdout.write(self.style.SUCCESS(
                    f'✓ [{i + 1}/{total_chunks}] Saved "{chunk_title}"'
                ))

            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Ingested "{title}" ({total_chunks} chunk(s)) into RAG knowledge base'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Error: {e}'))
            raise
