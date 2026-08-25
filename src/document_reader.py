from io import BytesIO

from docx import Document
from pypdf import PdfReader


def read_uploaded_document(uploaded_file):
    """
    Extract text from an uploaded business document.

    Supported formats:
    - TXT
    - CSV
    - PDF
    - DOCX
    """

    filename = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()

    # TXT
    if filename.endswith(".txt"):
        return file_bytes.decode(
            "utf-8",
            errors="ignore"
        )

    # CSV
    if filename.endswith(".csv"):
        return file_bytes.decode(
            "utf-8",
            errors="ignore"
        )

    # PDF
    if filename.endswith(".pdf"):

        pdf_file = BytesIO(file_bytes)

        reader = PdfReader(pdf_file)

        pages = []

        for page_number, page in enumerate(
            reader.pages,
            start=1
        ):

            page_text = page.extract_text()

            if page_text:

                pages.append(
                    f"\n--- Page {page_number} ---\n"
                    f"{page_text}"
                )

        return "\n".join(pages)

    # WORD
    if filename.endswith(".docx"):

        word_file = BytesIO(file_bytes)

        document = Document(word_file)

        paragraphs = []

        for paragraph in document.paragraphs:

            if paragraph.text.strip():

                paragraphs.append(
                    paragraph.text
                )

        return "\n".join(paragraphs)

    raise ValueError(
        "Unsupported document type. "
        "Please upload PDF, DOCX, TXT or CSV."
    )