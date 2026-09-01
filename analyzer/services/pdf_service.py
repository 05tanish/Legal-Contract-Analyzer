import pymupdf
import logging

logger = logging.getLogger(__name__)

def extract_pdf_pages(file_path):
    """
    Extracts text from a PDF file page by page.
    Returns a list of dictionaries: [{'page': 1, 'text': '...'}, ...]
    """
    pages = []
    try:
        doc = pymupdf.open(file_path)
        for i in range(len(doc)):
            page = doc.load_page(i)
            text = page.get_text("text").strip()
            pages.append({
                "page": i + 1,
                "text": text
            })
    except Exception as e:
        logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
        raise e
    return pages
