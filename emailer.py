from datetime import datetime
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from db.mongo import db
from db.users import EmailLog
import utils

def send_email(*, email: str, subject: str, content: str, type: str) -> None:
    """
    Send an email via Gmail SMTP and log the email to the database.
    Requires environment variables:
      - SMTP_HOST (default: smtp.gmail.com)
      - SMTP_PORT (default: 587)
      - SMTP_USERNAME (Gmail address)
      - SMTP_PASSWORD (Gmail App Password)
      - SMTP_FROM (defaults to SMTP_USERNAME)
    """
    try:
        log = EmailLog(
            email=email,
            subject=subject,
            content=content,
            type=type,
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        res = db["email_logs"].insert_one(log.model_dump())
        utils.logger.info(f"Email log created with id: {res.inserted_id} for {email} [{type}]")

        # Prepare SMTP config
        SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
        SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        SMTP_USERNAME = os.getenv("SMTP_USERNAME")
        SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
        SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME)

        if not SMTP_USERNAME or not SMTP_PASSWORD:
            raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be set in environment variables")

        # Build email
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(content, "plain"))

        # Send via TLS
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [email], msg.as_string())

        # Mark as sent
        db["email_logs"].update_one({"_id": res.inserted_id}, {"$set": {"status": "sent", "updated_at": datetime.now()}})
        utils.logger.info(f"Email sent to {email}: {subject}")
    except Exception as e:
        utils.logger.error(f"Failed to log/send email to {email}: {e}")
        try:
            db["email_logs"].insert_one({
                "email": email,
                "subject": subject,
                "content": content,
                "type": type,
                "status": "failed",
                "error": str(e),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            })
        except Exception:
            pass
