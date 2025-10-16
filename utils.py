import hashlib
import smtplib
from email.message import EmailMessage
import logging 
import os
import re,json
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

def send_email(listing_id):
    # Your credentials and SMTP settings
    EMAIL_ADDRESS = "leboncoin.me.assistant@gmail.com"
    EMAIL_PASSWORD = "gytfbueqmkpfkghs" 
    to_email= "ayoub.touti@icloud.com"
    json_path = get_json_session_path(listing_id)
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            messages = json.load(f)
    conversation_text = "\n".join(
    f"{msg['role'].capitalize()}: {msg['content']}"
    for msg in messages[1:] # skip the system message 
    )
    

    database_manager = DatabaseManager()
    listing_information = database_manager.retrieve_listing(listing_id)
    if listing_information:
        id_, title, price, url, location, date, description = listing_information

        listing_information_text = f"""
    📌 Listing Information
    -------------------------
    Title      : {title}
    Price      : {price}
    Location   : {location}
    Date       : {date}
    URL        : {url}
    Description: {description}
    -------------------------
    """
        print(listing_information_text)
    else:
        logger.warning("No listing found with that ID.")

    msg = EmailMessage()
    msg["Subject"] = "Assistant Report"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    body = f"""
    Your assistant has found a new opportunity:
    The listing : 
    {listing_information_text}
    
    The conversation :
    {conversation_text}
    """
    msg.set_content(body)

    # Send email via Gmail SMTP
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
        logger.info(f"Email sent to {to_email} ✅")

if __name__=='__main__':


    send_email(
        listing_id="fix"
    )
