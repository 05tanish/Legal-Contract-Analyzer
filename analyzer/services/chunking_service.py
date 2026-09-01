import re

def create_chunks(pages_list, max_chunk_length=800):
    """
    Takes a list of pages [{'page': int, 'text': str}, ...]
    and splits the text into logical chunks (paragraphs).
    Returns [{'page': int, 'text': str}, ...]
    """
    chunks = []
    
    for page_obj in pages_list:
        page_num = page_obj['page']
        text = page_obj['text']
        
        # Split by double newlines or similar paragraph breaks
        paragraphs = re.split(r'\n\s*\n', text)
        
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
                
            # If paragraph is too long, split it roughly by sentence punctuation
            if len(p) > max_chunk_length:
                sentences = re.split(r'(?<=[.!?])\s+', p)
                current_chunk = ""
                for s in sentences:
                    if len(current_chunk) + len(s) < max_chunk_length:
                        current_chunk += s + " "
                    else:
                        if current_chunk:
                            chunks.append({
                                "page": page_num,
                                "text": current_chunk.strip()
                            })
                        current_chunk = s + " "
                if current_chunk:
                    chunks.append({
                        "page": page_num,
                        "text": current_chunk.strip()
                    })
            else:
                chunks.append({
                    "page": page_num,
                    "text": p
                })
                
    return chunks
