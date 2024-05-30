# generate.py
from flask import jsonify, send_file
import fitz
import io
import traceback

def generate_individual_pdf(input_pdf, replacements, list_replacements=[]):
    try:
        doc = fitz.open(input_pdf)
        output_doc = fitz.open()
        for data in list_replacements:
            for page in doc:
                new_page = output_doc.new_page(-1, width=page.rect.width, height=page.rect.height)
                new_page.show_pdf_page(page.rect, doc, page.number - 1)
                combined_replacements = {**replacements, **data}
                for key, value in combined_replacements.items():
                    text_instances = page.search_for(f"{{{key.upper()}}}")
                    for inst in text_instances:
                        rect = fitz.Rect(inst[0], inst[1], inst[2], inst[3])
                        new_page.add_redact_annot(rect, fill=(1, 1, 1))
                        new_page.apply_redactions()
                        new_page.insert_text((rect.x0, rect.y1), str(value), fontsize=9, fontname='helv', rotate=0)
        pdf_bytes = io.BytesIO()
        output_doc.save(pdf_bytes, deflate=True)
        pdf_bytes.seek(0)
        doc.close()
        output_doc.close()
        return send_file(pdf_bytes, download_name="modified_output.pdf", as_attachment=True)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500

def generate_summary_pdf(input_pdf, first, middle, last, replacements, list_replacements=[]):
    try:
        doc = fitz.open(input_pdf)
        output_doc = fitz.open()

        num_middle_records = len(list_replacements) - first - last
        num_middle_pages = num_middle_records // middle
        if num_middle_records % middle > 0:
            num_middle_pages += 1

        first_page_replacements = list_replacements[:first]
        middle_page_replacements = [list_replacements[i:i+middle] for i in range(first, first + num_middle_pages * middle, middle)]
        last_page_replacements = list_replacements[len(first_page_replacements) + len(middle_page_replacements) * middle:]

        # First page
        page = doc[0]
        new_page = output_doc.new_page(-1, width=page.rect.width, height=page.rect.height)
        new_page.show_pdf_page(page.rect, doc, page.number)
        # for 6 list_replacements create a new dict adding the index to the key
        combined_replacements = {**replacements}
        for i, data in enumerate(first_page_replacements):
            for key, value in data.items():
                # 01, 02, 03, 04, 05, 06
                combined_replacements[f"{key.upper()}{i+1:02d}" if key != "Comune" else key] = value
        for key, value in combined_replacements.items():
            text_instances = page.search_for(f"{{{key.upper()}}}")
            for inst in text_instances:
                rect = fitz.Rect(inst[0], inst[1], inst[2], inst[3])
                new_page.add_redact_annot(rect, fill=(1, 1, 1))
                new_page.apply_redactions()
                new_page.insert_text((rect.x0, rect.y1), str(value), fontsize=9, fontname='helv', rotate=0)


        # Middle pages
        page = doc[1]
        for data in middle_page_replacements:
            new_page = output_doc.new_page(-1, width=page.rect.width, height=page.rect.height)
            new_page.show_pdf_page(page.rect, doc, page.number)
            combined_replacements = {**replacements}
            for i, data in enumerate(data):
                for key, value in data.items():
                    # 01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13
                    combined_replacements[f"{key.upper()}{i+1:02d}" if key != "Comune" else key] = value
            for key, value in combined_replacements.items():
                text_instances = page.search_for(f"{{{key.upper()}}}")
                for inst in text_instances:
                    rect = fitz.Rect(inst[0], inst[1], inst[2], inst[3])
                    new_page.add_redact_annot(rect, fill=(1, 1, 1))
                    new_page.apply_redactions()
                    new_page.insert_text((rect.x0, rect.y1), str(value), fontsize=9, fontname='helv', rotate=0)

        # Last page
        page = doc[2]
        new_page = output_doc.new_page(-1, width=page.rect.width, height=page.rect.height)
        new_page.show_pdf_page(page.rect, doc, page.number)
        combined_replacements = {**replacements}
        for i, data in enumerate(last_page_replacements):
            for key, value in data.items():
                # 01, 02, 03, 04, 05, 06, 07, 08
                combined_replacements[f"{key.upper()}{i+1:02d}" if key != "Comune" else key] = value
        for key, value in combined_replacements.items():
            text_instances = page.search_for(f"{{{key.upper()}}}")
            for inst in text_instances:
                rect = fitz.Rect(inst[0], inst[1], inst[2], inst[3])
                new_page.add_redact_annot(rect, fill=(1, 1, 1))
                new_page.apply_redactions()
                new_page.insert_text((rect.x0, rect.y1), str(value), fontsize=9, fontname='helv', rotate=0)

        pdf_bytes = io.BytesIO()
        output_doc.save(pdf_bytes, deflate=True)
        pdf_bytes.seek(0)
        doc.close()
        output_doc.close()
        return send_file(pdf_bytes, download_name="modified_output.pdf", as_attachment=True)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred: " + str(e)}), 500



