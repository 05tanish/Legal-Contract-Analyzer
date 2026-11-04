import fitz  # PyMuPDF
from typing import List, Dict, Any
import hashlib
import os
import logging

logger = logging.getLogger(__name__)

# Safe optional pymupdf4llm import
try:
    import pymupdf4llm
    PYMUPDF4LLM_AVAILABLE = True
except Exception as e:
    logger.warning(f"pymupdf4llm could not be loaded ({e}). Raw PyMuPDF fallback will be used.")
    pymupdf4llm = None
    PYMUPDF4LLM_AVAILABLE = False

class DocumentParser:
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Computes SHA-256 hash of a contract file to avoid duplicate indexing."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def parse_pdf(file_path: str) -> Dict[str, Any]:
        """
        Extracts layout-aware structured markdown from a PDF document.
        Preserves headers, table layouts, and per-page boundaries.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Contract file not found at: {file_path}")

        doc = fitz.open(file_path)
        total_pages = len(doc)
        pages_data = []

        try:
            if not PYMUPDF4LLM_AVAILABLE or pymupdf4llm is None:
                raise ImportError("pymupdf4llm not available, using raw PyMuPDF parser.")

            # Use pymupdf4llm to extract structured markdown with page chunks
            # to preserve headings (# Article 1), tables, and formatting
            md_pages = pymupdf4llm.to_markdown(file_path, page_chunks=True)
            
            for item in md_pages:
                page_num = item.get("metadata", {}).get("page", 1)
                text = item.get("text", "").strip()
                
                # Extract potential headings in this page
                headings = [line.strip("# ").strip() for line in text.split("\n") if line.strip().startswith("#")]
                
                pages_data.append({
                    "page_number": page_num,
                    "content": text,
                    "headings": headings,
                    "token_estimate": len(text.split())
                })

            # If all extracted pages are empty, trigger raw fitz fallback
            if not any(p.get("content") for p in pages_data) and total_pages > 0:
                pages_data.clear()
                for page_idx in range(total_pages):
                    page = doc.load_page(page_idx)
                    text = page.get_text("text").strip()
                    pages_data.append({
                        "page_number": page_idx + 1,
                        "content": text,
                        "headings": [],
                        "token_estimate": len(text.split())
                    })
        except Exception as e:
            logger.warning(f"pymupdf4llm fallback triggered due to: {e}")
            # Robust fallback to raw fitz extraction
            for page_idx in range(total_pages):
                page = doc.load_page(page_idx)
                text = page.get_text("text").strip()
                pages_data.append({
                    "page_number": page_idx + 1,
                    "content": text,
                    "headings": [],
                    "token_estimate": len(text.split())
                })
        finally:
            doc.close()

        file_size = os.path.getsize(file_path)
        file_hash = DocumentParser.calculate_file_hash(file_path)

        return {
            "file_hash": file_hash,
            "file_size_bytes": file_size,
            "total_pages": total_pages,
            "pages": pages_data
        }

