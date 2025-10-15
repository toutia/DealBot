import hashlib

def message_hash(text: str) -> str:
    """Generate a unique hash for a message based on text """
    base = f"{text.strip()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()