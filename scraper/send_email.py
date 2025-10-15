import smtplib
from email.message import EmailMessage
import logging 

logger = logging.getLogger(__name__)


def send_email(subject, body, to_email):
    # Your credentials and SMTP settings
    EMAIL_ADDRESS = "leboncoin.me.assistant@gmail.com"
    EMAIL_PASSWORD = "gytfbueqmkpfkghs"  # 

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg.set_content(body)

    # Send email via Gmail SMTP
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
        print(f"Email sent to {to_email} ✅")

# Example usage
send_email(
    subject="Scraper Report",
    body="Your scraper has found new listings.",
    to_email="ayoub.touti@icloud.com"
)



