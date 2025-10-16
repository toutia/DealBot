import os
import json
import smtplib
from email.message import EmailMessage
from database import DatabaseManager
from utils import get_json_session_path
import logging
import re

logger = logging.getLogger(__name__)

config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
with open(config_path) as f:
    credentials = json.load(f)['gmail']
  


def clean_text(text: str) -> str:
    """Remove linefeeds, tabs, and excessive spaces."""
    if not text:
        return "N/A"
    text = re.sub(r"[\n\r\t]+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def send_listing_report(listing_id):
    json_path = get_json_session_path(listing_id)

    # Load conversation
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            messages = json.load(f)
    else:
        logger.warning(f"No conversation JSON found for {listing_id}")
        messages = []

    # Convert conversation to HTML list
    conversation_html = ""
    for msg in messages[1:]:  # skip system
        role = msg["role"].capitalize()
        content = clean_text(msg["content"]).replace("\n", "<br>")

        # Unified left alignment
        bg_color = "#e6f3ff" if msg["role"] == "assistant" else "#f0f0f0"
        color = "#1a73e8" if msg["role"] == "assistant" else "#333"

        conversation_html += f"""
        <li style="background:{bg_color}; padding:10px; border-radius:8px; margin-bottom:8px; list-style:none; text-align:left;">
          <strong style="color:{color};">{role}:</strong> {content}
        </li>
        """

    # Retrieve listing info
    db = DatabaseManager()
    listing_info = db.retrieve_listing(listing_id)

    if not listing_info:
        logger.warning("No listing found with that ID.")
        return

    id_, title, price, url, location, date, description = listing_info

    # Clean all fields
    title = clean_text(title)
    price = clean_text(price)
    url = clean_text(url)
    location = clean_text(location)
    date = clean_text(date)
    description = clean_text(description)

    safe_title = " ".join((title or "Untitled").split())

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color:#f9f9f9; padding:20px;">
      <div style="max-width:600px; margin:auto; background-color:#ffffff; border-radius:10px; padding:20px; box-shadow:0 2px 5px rgba(0,0,0,0.1);">
        <h2 style="color:#333; text-align:center;">💬 Assistant Report</h2>

        <h3 style="color:#555;">📌 Listing Information</h3>
        <table style="width:100%; border-collapse:collapse;">
          <tr><td style="padding:4px 0;"><strong>Title:</strong></td><td>{title}</td></tr>
          <tr><td style="padding:4px 0;"><strong>Price:</strong></td><td>{price}</td></tr>
          <tr><td style="padding:4px 0;"><strong>Location:</strong></td><td>{location}</td></tr>
          <tr><td style="padding:4px 0;"><strong>Date:</strong></td><td>{date}</td></tr>
          <tr><td style="padding:4px 0;"><strong>Description:</strong></td><td>{description}</td></tr>
        </table>

        <p style="margin-top:20px;">
          <a href="{url}" style="color:#1a73e8; text-decoration:none;">View Listing on Leboncoin →</a>
        </p>

        <hr style="margin:25px 0; border:none; border-top:1px solid #ddd;">

        <h3 style="color:#555;">🗨️ Conversation Summary</h3>
        <ul style="padding-left:0; margin:0; list-style:none; font-size:14px; line-height:1.5;">
          {conversation_html}
        </ul>

        <div style="text-align:center; margin-top:30px;">
          <a href="{url}" style="background-color:#28a745; color:white; padding:12px 20px; text-decoration:none; border-radius:6px; font-weight:bold; display:inline-block;">
            ✅ Finish the Transaction
          </a>
        </div>

        <p style="text-align:center; color:#999; font-size:12px; margin-top:20px;">
          — Sent automatically by DealBot —
        </p>
      </div>
    </body>
    </html>
    """

    # Plain text fallback
    conversation_text = "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}" for msg in messages[1:]
    )

    plain_body = f"""
Assistant Report

Listing:
Title: {title}
Price: {price}
Location: {location}
Date: {date}
Description: {description}
URL: {url}

Conversation:
{conversation_text}

Finish the transaction: {url}
"""

    msg = EmailMessage()
    msg["Subject"] = f"DealBot Report: {safe_title}"
    msg["From"] = credentials['email']
    msg["To"] = credentials['to_email']
    msg.set_content(plain_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(credentials['email'], credentials['password'])
        smtp.send_message(msg)
        logger.info(f"📨 Email sent to {credentials['to_email']} ✅")



if __name__=='__main__':
    send_listing_report('3067309470')