from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from .config import PORTFOLIO_URL


def wa_link(business_name: str) -> str:
    number = os.getenv("WA_NUMBER", "").strip().replace("+", "").replace(" ", "").replace("-", "")
    if not number:
        return ""
    text = f"Halo Rey, saya dari {business_name}. Saya ingin melihat detail jasa landing page."
    return f"https://wa.me/{number}?text={quote(text)}"


def build_message(body: str, business_name: str) -> str:
    link = wa_link(business_name)
    return (
        body.strip()
        + "\n\nPortofolio:\n"
        + PORTFOLIO_URL
        + "\n\nLanjut via WhatsApp:\n"
        + link
    )


def send_email(to_email: str, subject: str, body: str) -> None:
    user = os.getenv("GMAIL_ADDRESS", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "").strip()
    if not user or not password:
        raise RuntimeError("GMAIL_ADDRESS / GMAIL_APP_PASSWORD belum diisi")
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = (subject or "Ide landing page untuk bisnis Anda")[:120]
    msg.set_content(body)
    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
        server.starttls(context=context)
        server.login(user, password)
        server.send_message(msg)
