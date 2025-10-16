import hashlib
import smtplib
from email.message import EmailMessage
import logging 
import os
import re,json
import uuid
from  database import DatabaseManager
logger = logging.getLogger(__name__)

# ---- CONFIG ----
MODEL_PATH = "/home/touti/models/gpt-oss-20b-fp16.gguf"

SESSIONS_DIR = os.path.join(os.path.dirname('__file__'), 'sessions')


def message_hash(text: str) -> str:
    """Generate a unique hash for a message based on text """
    base = f"{text.strip()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def get_json_session_path(chat_id: str) -> str:
    return os.path.join(SESSIONS_DIR, f"{chat_id}.json")

def get_state_path(chat_id: str) -> str:
    return os.path.join(SESSIONS_DIR, f"{chat_id}.pkl")

def extract_final_message(raw_content: str) -> str:
    """
    Extract only the final assistant message from the model output.
    """
    pattern = r"<\|start\|>assistant<\|channel\|>final<\|message\|>(.*)"
    match = re.search(pattern, raw_content, re.DOTALL)
    if match:
        # Clean leading/trailing whitespace
        return match.group(1).strip()
    return raw_content.strip()  # fallback

def is_valid_uuid(id_value):

    try:
        uuid_obj = uuid.UUID(id_value, version=4)
        assert str(uuid_obj) == id_value
        return True
    except ValueError:
        return False
