from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from .config import PORTFOLIO_URL


def wa_link(business_name: str) -> str:
    number = (
        os.getenv("WA_NUMBER", "")
        .strip()
        .replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if not number:
        return ""

    text = (
        f"Halo Rey, saya dari {business_name}. "
        "Saya ingin melihat detail jasa landing page."
    )

    return f"https://wa.me/{number}?text={quote(text)}"


def _remove_whatsapp_footer(body: str) -> str:
    marker = "Lanjut via WhatsApp:"

    if marker not in body:
        return body.strip()

    return body.split(marker, 1)[0].strip()


def _remove_duplicate_portfolio(body: str) -> str:
    body = body.strip()

    if PORTFOLIO_URL not in body:
        return body

    first_position = body.find(PORTFOLIO_URL)

    prefix = body[:first_position]
    suffix = body[first_position + len(PORTFOLIO_URL):]

    while PORTFOLIO_URL in suffix:
        suffix = suffix.replace(PORTFOLIO_URL, "")

    return (prefix + PORTFOLIO_URL + suffix).strip()


def _ensure_portfolio(body: str) -> str:
    body = _remove_duplicate_portfolio(body)

    if PORTFOLIO_URL in body:
        return body

    return (
        body
        + "\n\nPortofolio:\n"
        + PORTFOLIO_URL
    )


def build_message(
    body: str,
    business_name: str,
) -> str:

    body = body or ""

    body = _remove_whatsapp_footer(body)

    body = _ensure_portfolio(body)

    link = wa_link(business_name).strip()

    if link:
        body = (
            body.rstrip()
            + "\n\nLanjut via WhatsApp:\n"
            + link
        )

    return body.strip()


def send_email(
    to_email: str,
    subject: str,
    body: str,
) -> None:

    user = os.getenv(
        "GMAIL_ADDRESS",
        "",
    ).strip()

    password = os.getenv(
        "GMAIL_APP_PASSWORD",
        "",
    ).replace(" ", "").strip()

    if not user or not password:
        raise RuntimeError(
            "GMAIL_ADDRESS / GMAIL_APP_PASSWORD belum diisi"
        )

    msg = EmailMessage()

    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = (
        subject
        or "Ide landing page untuk bisnis Anda"
    )[:120]

    msg.set_content(body)

    context = ssl.create_default_context()

    with smtplib.SMTP(
        "smtp.gmail.com",
        587,
        timeout=30,
    ) as server:

        server.starttls(context=context)

        server.login(
            user,
            password,
        )

        server.send_message(msg)
