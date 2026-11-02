import re
import string

def preprocess_text(text):
    """
    Cleans legal text. Matches the exact logic used during the CUAD ML training.
    """
    if not isinstance(text, str):
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Remove HTML tags if any exist
    text = re.sub(r'<[^>]+>', '', text)
    
    # Keep important legal stop words but remove standard punctuation
    # We replace punctuation with spaces to avoid joining words
    text = text.translate(str.maketrans(string.punctuation, ' ' * len(string.punctuation)))
    
    # Remove extra whitespaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text
