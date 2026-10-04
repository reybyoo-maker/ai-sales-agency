from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from .config import PORTFOLIO_URL


def wa_link(business_name: str) -> str:
    """
    Membuat link WhatsApp otomatis berdasarkan nomor
    yang disimpan di environment variable WA_NUMBER.
    """

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

    return (
        f"https://wa.me/{number}"
        f"?text={quote(text)}"
    )


def _remove_whatsapp_footer(body: str) -> str:
    """
    Menghapus footer WhatsApp lama jika Gemini
    secara tidak sengaja sudah membuatnya.
    """

    marker = "Lanjut via WhatsApp:"

    if marker not in body:
        return body.strip()

    body = body.split(
        marker,
        1,
    )[0]

    return body.strip()


def _ensure_portfolio(
    body: str,
) -> str:
    """
    Memastikan portfolio hanya muncul sekali.

    Jika URL sudah ada di body, tidak menambahkan
    portfolio kedua.
    """

    body = body.strip()

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
    """
    Membentuk final email:

    1. Bersihkan footer WhatsApp dari Gemini.
    2. Pastikan portfolio hanya sekali.
    3. Tambahkan link WhatsApp sekali.
    """

    body = body or ""

    body = _remove_whatsapp_footer(
        body
    )

    body = _ensure_portfolio(
        body
    )

    link = wa_link(
        business_name
    ).strip()

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

    user = (
        os.getenv(
            "GMAIL_ADDRESS",
            "",
        )
        .strip()
    )

    password = (
        os.getenv(
            "GMAIL_APP_PASSWORD",
            "",
        )
        .replace(" ", "")
        .strip()
    )

    if not user or not password:
        raise RuntimeError(
            "GMAIL_ADDRESS / "
            "GMAIL_APP_PASSWORD "
            "belum diisi"
        )

    msg = EmailMessage()

    msg["From"] = user

    msg["To"] = to_email

    msg["Subject"] = (
        subject
        or "Ide landing page untuk bisnis Anda"
    )[:120]

    msg.set_content(
        body
    )

    context = ssl.create_default_context()

    with smtplib.SMTP(
        "smtp.gmail.com",
        587,
        timeout=30,
    ) as server:

        server.starttls(
            context=context
        )

        server.login(
            user,
            password,
        )

        server.send_message(
            msg
        )
