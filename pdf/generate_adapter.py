"""
Adapter between event payloads and existing PDF generation logic.
Converts event data to PDF bytes (not Flask responses).
"""
import fitz
import io
import os
import logging

logger = logging.getLogger(__name__)


def generate_pdf_from_template(template_name, data):
    """
    Generate PDF bytes from template name and data dict.

    Args:
        template_name: e.g. "individuale", "riepilogativo", "individual", "summary"
        data: Dict with 'replacements' and 'list_replacements'

    Returns:
        bytes: PDF content

    Raises:
        ValueError: If template not found
        Exception: If generation fails
    """
    # Normalize template name
    template_name_lower = template_name.lower()

    if 'individual' in template_name_lower or 'individuale' in template_name_lower:
        return _generate_individual(data)
    elif 'summary' in template_name_lower or 'riepilogativ' in template_name_lower:
        return _generate_summary(data)
    else:
        raise ValueError(f"Unknown template: {template_name}")


def _generate_individual(data):
    """
    Generate individual PDF (one page per record).

    Args:
        data: Dict with 'replacements' (common fields) and 'list_replacements' (per-record fields)

    Returns:
        bytes: PDF content
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    input_pdf = os.path.join(base_path, 'templates', 'individuale.pdf')

    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Template not found: {input_pdf}")

    replacements = data.get('replacements', {})
    list_replacements = data.get('list_replacements', [])

    if not list_replacements:
        logger.warning("No list_replacements provided, using empty list")
        list_replacements = [{}]  # At least one page

    try:
        doc = fitz.open(input_pdf)
        output_doc = fitz.open()

        # Generate one page per record
        for record_data in list_replacements:
            for page in doc:
                # Create new page
                new_page = output_doc.new_page(-1, width=page.rect.width, height=page.rect.height)
                new_page.show_pdf_page(page.rect, doc, page.number)

                # Combine common replacements with record-specific data
                combined_replacements = {**replacements, **record_data}

                # Replace placeholders {KEY}
                for key, value in combined_replacements.items():
                    text_instances = page.search_for(f"{{{key.upper()}}}")
                    for inst in text_instances:
                        rect = fitz.Rect(inst[0], inst[1], inst[2], inst[3])
                        new_page.add_redact_annot(rect, fill=(1, 1, 1))
                        new_page.apply_redactions()
                        new_page.insert_text(
                            (rect.x0, rect.y1),
                            str(value),
                            fontsize=9,
                            fontname='helv',
                            rotate=0
                        )

        # Save to bytes
        pdf_bytes = io.BytesIO()
        output_doc.save(pdf_bytes, deflate=True)
        doc.close()
        output_doc.close()

        return pdf_bytes.getvalue()

    except Exception as e:
        logger.error(f"Failed to generate individual PDF: {e}", exc_info=True)
        raise


def _generate_summary(data):
    """
    Generate summary PDF (multi-page with pagination).

    Args:
        data: Dict with:
            - 'replacements': Common fields
            - 'list_replacements': List of records
            - 'first': Number of records on first page (default 6)
            - 'middle': Number of records per middle page (default 13)
            - 'last': Number of records on last page (default 8)

    Returns:
        bytes: PDF content
    """
    base_path = os.path.dirname(os.path.abspath(__file__))
    input_pdf = os.path.join(base_path, 'templates', 'riepilogativo.pdf')

    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Template not found: {input_pdf}")

    replacements = data.get('replacements', {})
    list_replacements = data.get('list_replacements', [])
    first = data.get('first', 6)
    middle = data.get('middle', 13)
    last = data.get('last', 8)

    if not list_replacements:
        logger.warning("No list_replacements provided for summary")
        list_replacements = [{}]

    try:
        doc = fitz.open(input_pdf)
        output_doc = fitz.open()

        # Calculate pagination
        num_middle_records = len(list_replacements) - first - last
        num_middle_pages = max(0, num_middle_records // middle)
        if num_middle_records % middle > 0:
            num_middle_pages += 1

        first_page_replacements = list_replacements[:first]
        middle_start = first
        middle_page_replacements = [
            list_replacements[i:i+middle]
            for i in range(middle_start, middle_start + num_middle_pages * middle, middle)
        ]
        last_page_replacements = list_replacements[first + num_middle_pages * middle:]

        # First page
        if doc.page_count > 0:
            page = doc[0]
            new_page = output_doc.new_page(-1, width=page.rect.width, height=page.rect.height)
            new_page.show_pdf_page(page.rect, doc, 0)

            combined_replacements = {**replacements}
            for i, record in enumerate(first_page_replacements):
                for key, value in record.items():
                    # Create indexed keys: COGNOME01, COGNOME02, etc.
                    indexed_key = f"{key.upper()}{i+1:02d}" if key.upper() != "COMUNE" else key.upper()
                    combined_replacements[indexed_key] = value

            _apply_replacements(page, new_page, combined_replacements)

        # Middle pages
        if doc.page_count > 1 and middle_page_replacements:
            page = doc[1]
            for page_records in middle_page_replacements:
                new_page = output_doc.new_page(-1, width=page.rect.width, height=page.rect.height)
                new_page.show_pdf_page(page.rect, doc, 1)

                combined_replacements = {**replacements}
                for i, record in enumerate(page_records):
                    for key, value in record.items():
                        indexed_key = f"{key.upper()}{i+1:02d}" if key.upper() != "COMUNE" else key.upper()
                        combined_replacements[indexed_key] = value

                _apply_replacements(page, new_page, combined_replacements)

        # Last page
        if doc.page_count > 2 and last_page_replacements:
            page = doc[2]
            new_page = output_doc.new_page(-1, width=page.rect.width, height=page.rect.height)
            new_page.show_pdf_page(page.rect, doc, 2)

            combined_replacements = {**replacements}
            for i, record in enumerate(last_page_replacements):
                for key, value in record.items():
                    indexed_key = f"{key.upper()}{i+1:02d}" if key.upper() != "COMUNE" else key.upper()
                    combined_replacements[indexed_key] = value

            _apply_replacements(page, new_page, combined_replacements)

        # Save to bytes
        pdf_bytes = io.BytesIO()
        output_doc.save(pdf_bytes, deflate=True)
        doc.close()
        output_doc.close()

        return pdf_bytes.getvalue()

    except Exception as e:
        logger.error(f"Failed to generate summary PDF: {e}", exc_info=True)
        raise


def _apply_replacements(source_page, target_page, replacements):
    """
    Apply text replacements to a page.

    Args:
        source_page: Source PDF page (for searching placeholders)
        target_page: Target page to write to
        replacements: Dict of {KEY: value} replacements
    """
    for key, value in replacements.items():
        text_instances = source_page.search_for(f"{{{key.upper()}}}")
        for inst in text_instances:
            rect = fitz.Rect(inst[0], inst[1], inst[2], inst[3])
            target_page.add_redact_annot(rect, fill=(1, 1, 1))
            target_page.apply_redactions()
            target_page.insert_text(
                (rect.x0, rect.y1),
                str(value),
                fontsize=9,
                fontname='helv',
                rotate=0
            )
