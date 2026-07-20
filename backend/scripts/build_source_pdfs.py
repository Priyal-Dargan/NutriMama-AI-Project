"""
scripts/build_source_pdfs.py
One-time utility: converts the plain-text files in rag/source_texts/ into actual
PDF files in rag/documents/, so the RAG pipeline's PyPDF2-based ingestion path
(rag/loader.py) has real PDFs to process, per the spec's PyPDF2 requirement.

Run manually if you add/edit a source text file:
    python scripts/build_source_pdfs.py
"""

import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

SOURCE_DIR = os.path.join(os.path.dirname(__file__), "..", "rag", "source_texts")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "rag", "documents")


def text_to_pdf(txt_path: str, pdf_path: str) -> None:
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    for line in text.split("\n"):
        safe_line = line.encode("latin-1", "replace").decode("latin-1")
        if safe_line.strip() == "":
            pdf.ln(4)  # blank line -> just add vertical spacing, don't call multi_cell on empty text
        else:
            pdf.multi_cell(0, 6, safe_line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(pdf_path)
    print(f"Wrote {pdf_path}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for filename in sorted(os.listdir(SOURCE_DIR)):
        if not filename.endswith(".txt"):
            continue
        txt_path = os.path.join(SOURCE_DIR, filename)
        pdf_path = os.path.join(OUTPUT_DIR, filename.replace(".txt", ".pdf"))
        text_to_pdf(txt_path, pdf_path)


if __name__ == "__main__":
    main()
