from __future__ import annotations
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from urllib.parse import quote

from .config import WA_NUMBER, PORTFOLIO_URL


def wa_link(prefill: str) -> str:
    if not WA_NUMBER:
        raise RuntimeError('WA_NUMBER is missing')
    number = ''.join(ch for ch in WA_NUMBER if ch.isdigit())
    if number.startswith('0'):
        number = '62' + number[1:]
    return f'https://wa.me/{number}?text={quote(prefill)}'


def build_message_body(generated: dict, business_name: str) -> str:
    body = generated['body'].strip()
    link = wa_link(f'Halo Rey, saya dari {business_name}. Saya tertarik dengan landing page dan ingin lihat detailnya.')
    return f"{body}\n\nPortofolio: {PORTFOLIO_URL}\nLanjut via WhatsApp: {link}"


def send_email(to: str, subject: str, body: str):
    user = os.environ.get('GMAIL_ADDRESS')
    password = os.environ.get('GMAIL_APP_PASSWORD')
    if not user or not password:
        raise RuntimeError('GMAIL_ADDRESS/GMAIL_APP_PASSWORD is missing')
    msg = EmailMessage()
    msg['From'] = user
    msg['To'] = to
    msg['Subject'] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
