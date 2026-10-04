from __future__ import annotations

import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from .config import PORTFOLIO_URL


def clean_text(value: str) -> str:
    """
    Membersihkan karakter tersembunyi dari data.
    """
    if not value:
        return ""

    return (
        str(value)
        .replace("\xa0", " ")
        .replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
        .strip()
    )


def clean_email_address(value: str) -> str:
    """
    Membersihkan alamat email dari karakter tersembunyi.
    Alamat email normal harus ASCII.
    """
    value = clean_text(value)

    # Hapus seluruh whitespace di sekitar alamat.
    value = re.sub(r"\s+", "", value)

    return value


def valid_email_address(value: str) -> bool:
    """
    Validasi dasar email.
    """
    value = clean_email_address(value)

    if not value:
        return False

    if not re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
        r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+",
        value,
    ):
        return False

    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        return False

    return True


def wa_link(business_name: str) -> str:
    number = (
        os.getenv(
            "WA_NUMBER",
            "",
        )
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
    marker = "Lanjut via WhatsApp:"

    if marker not in body:
        return body.strip()

    return body.split(
        marker,
        1,
    )[0].strip()


def _remove_duplicate_portfolio(body: str) -> str:
    body = body.strip()

    if PORTFOLIO_URL not in body:
        return body

    first_position = body.find(
        PORTFOLIO_URL
    )

    prefix = body[:first_position]
    suffix = body[
        first_position + len(PORTFOLIO_URL):
    ]

    while PORTFOLIO_URL in suffix:
        suffix = suffix.replace(
            PORTFOLIO_URL,
            "",
        )

    return (
        prefix
        + PORTFOLIO_URL
        + suffix
    ).strip()


def _ensure_portfolio(body: str) -> str:
    body = _remove_duplicate_portfolio(
        body
    )

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

    body = clean_text(body)

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

    # Bersihkan alamat tujuan.
    to_email = clean_email_address(
        to_email
    )

    # Ambil alamat Gmail pengirim.
    user = clean_email_address(
        os.getenv(
            "GMAIL_ADDRESS",
            "",
        )
    )

    # Password App Password Gmail.
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

    if not valid_email_address(
        user
    ):
        raise RuntimeError(
            "GMAIL_ADDRESS tidak valid "
            "atau mengandung karakter tersembunyi"
        )

    if not valid_email_address(
        to_email
    ):
        raise RuntimeError(
            f"Alamat email tujuan tidak valid: "
            f"{to_email!r}"
        )

    subject = clean_text(
        subject
    ) or "Ide landing page untuk bisnis Anda"

    body = clean_text(
        body
    )

    msg = EmailMessage()

    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = subject[:120]

    # EmailMessage menangani encoding UTF-8
    # untuk isi email.
    msg.set_content(
        body,
        charset="utf-8",
    )

    context = ssl.create_default_context()

    with smtplib.SMTP(
        "smtp.gmail.com",
        587,
        timeout=30,
    ) as server:

        server.ehlo()

        server.starttls(
            context=context
        )

        server.ehlo()

        server.login(
            user,
            password,
        )

        server.send_message(
            msg
        )
