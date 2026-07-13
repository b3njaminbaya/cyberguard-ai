import hashlib
import hmac
import json
import os
import smtplib
from email.mime.text import MIMEText

import requests
from dotenv import load_dotenv

# Self-contained: don't rely on another module (e.g. database.py) happening
# to import first and trigger load_dotenv() as a side effect.
load_dotenv()

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USERNAME)


class NotificationError(Exception):
    pass


def send_slack(webhook_url: str, text: str) -> None:
    resp = requests.post(webhook_url, json={"text": text}, timeout=10)
    if resp.text.strip() != "ok":
        raise NotificationError(f"Slack rejected the message: {resp.status_code} {resp.text}")


def send_email(recipients: list[str], subject: str, body: str) -> None:
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        raise NotificationError(
            "SMTP_USERNAME / SMTP_PASSWORD not set in backend/.env — email delivery isn't configured."
        )
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, recipients, msg.as_string())


def send_webhook(url: str, payload: dict, secret: str | None = None) -> None:
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if secret:
        signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-CyberGuard-Signature"] = signature
    resp = requests.post(url, data=body, headers=headers, timeout=10)
    if not resp.ok:
        raise NotificationError(f"Webhook endpoint returned {resp.status_code}: {resp.text}")
