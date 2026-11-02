import uuid
from typing import List, Dict, Any
import re

class HierarchicalChunker:
    """
    Implements Hierarchical Parent-Child Chunking for complex legal contracts:
    - Parent chunks: Section/Article level (large context window, e.g. 800-1500 tokens)
    - Child chunks: Clause/Paragraph level (high-precision retrieval, e.g. 150-300 tokens)
    """

    def __init__(self, parent_max_words: int = 400, child_max_words: int = 120, overlap_words: int = 25):
        self.parent_max_words = parent_max_words
        self.child_max_words = child_max_words
        self.overlap_words = overlap_words

    def chunk_document(self, contract_id: str, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chunks_to_index = []
        chunk_index = 0

        for page in pages:
            page_num = page["page_number"]
            page_text = page["content"]

            if not page_text:
                continue

            # Split page text into parent blocks by double newline or headers
            raw_paragraphs = [p.strip() for p in re.split(r'\n{2,}|\n(?=#)', page_text) if p.strip()]

            # Group paragraphs into parent sections
            current_parent_words = []
            parent_chunks_temp = []

            for para in raw_paragraphs:
                words = para.split()
                if len(current_parent_words) + len(words) > self.parent_max_words and current_parent_words:
                    parent_chunks_temp.append(" ".join(current_parent_words))
                    current_parent_words = words
                else:
                    current_parent_words.extend(words)

            if current_parent_words:
                parent_chunks_temp.append(" ".join(current_parent_words))

            for parent_text in parent_chunks_temp:
                parent_id = str(uuid.uuid4())

                # Extract section title candidate
                section_title = None
                lines = parent_text.split("\n")
                if lines and (lines[0].startswith("#") or "SECTION" in lines[0].upper() or "ARTICLE" in lines[0].upper()):
                    section_title = lines[0].strip("# ").strip()[:100]

                # Store the Parent Chunk
                chunks_to_index.append({
                    "id": parent_id,
                    "contract_id": contract_id,
                    "chunk_index": chunk_index,
                    "page_number": page_num,
                    "section_title": section_title,
                    "content": parent_text,
                    "parent_id": None,
                    "is_parent": True,
                    "metadata": {
                        "page": page_num,
                        "is_parent": True,
                        "type": "parent_section"
                    }
                })
                chunk_index += 1

                # Subdivide Parent Chunk into Child Chunks for fine-grained retrieval
                words = parent_text.split()
                step = self.child_max_words - self.overlap_words
                if step <= 0:
                    step = self.child_max_words

                for i in range(0, len(words), step):
                    child_words = words[i:i + self.child_max_words]
                    child_text = " ".join(child_words)
                    child_id = str(uuid.uuid4())

                    # Contextual prefix: attach page & section context to child
                    context_prefix = f"[Page {page_num}" + (f" | {section_title}" if section_title else "") + "]: "
                    annotated_child_content = context_prefix + child_text

                    chunks_to_index.append({
                        "id": child_id,
                        "contract_id": contract_id,
                        "chunk_index": chunk_index,
                        "page_number": page_num,
                        "section_title": section_title,
                        "content": child_text,
                        "search_content": annotated_child_content,
                        "parent_id": parent_id,
                        "is_parent": False,
                        "metadata": {
                            "page": page_num,
                            "parent_id": parent_id,
                            "is_parent": False,
                            "section_title": section_title
                        }
                    })
                    chunk_index += 1

        return chunks_to_index

