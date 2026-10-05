from __future__ import annotations

import os
import re
import smtplib
import ssl
import unicodedata
from email.message import EmailMessage
from urllib.parse import quote

from .config import PORTFOLIO_URL


def normalize_value(value: str) -> str:
    """
    Membersihkan karakter Unicode/spasi tersembunyi.
    """
    if not value:
        return ""

    value = unicodedata.normalize(
        "NFKC",
        str(value),
    )

    # Menghapus semua whitespace Unicode,
    # termasuk NBSP (\xa0).
    value = "".join(value.split())

    return value.strip()


def clean_text(value: str) -> str:
    """
    Membersihkan teks biasa tanpa menghapus
    semua spasi di tengah kalimat.
    """
    if not value:
        return ""

    value = unicodedata.normalize(
        "NFKC",
        str(value),
    )

    value = (
        value
        .replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
        .replace("\xa0", " ")
    )

    return value.strip()


def clean_email_address(value: str) -> str:
    """
    Membersihkan alamat email agar ASCII-valid.
    """
    value = normalize_value(value)

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    return value


def valid_email_address(value: str) -> bool:
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


def wa_link(
    business_name: str,
) -> str:

    number = normalize_value(
        os.getenv(
            "WA_NUMBER",
            "",
        )
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


def _remove_whatsapp_footer(
    body: str,
) -> str:

    marker = "Lanjut via WhatsApp:"

    if marker not in body:
        return body.strip()

    return body.split(
        marker,
        1,
    )[0].strip()


def _remove_duplicate_portfolio(
    body: str,
) -> str:

    body = body.strip()

    if PORTFOLIO_URL not in body:
        return body

    first_position = body.find(
        PORTFOLIO_URL
    )

    prefix = body[:first_position]

    suffix = body[
        first_position
        + len(PORTFOLIO_URL):
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


def _ensure_portfolio(
    body: str,
) -> str:

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

    body = clean_text(
        body or ""
    )

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

    # Bersihkan email pengirim.
    user = clean_email_address(
        os.getenv(
            "GMAIL_ADDRESS",
            "",
        )
    )

    # PENTING:
    # ''.join(split()) menghapus SEMUA whitespace
    # Unicode, termasuk NBSP (\xa0).
    password = normalize_value(
        os.getenv(
            "GMAIL_APP_PASSWORD",
            "",
        )
    )

    # Bersihkan email penerima.
    to_email = clean_email_address(
        to_email
    )

    if not user or not password:
        raise RuntimeError(
            "GMAIL_ADDRESS / "
            "GMAIL_APP_PASSWORD belum diisi"
        )

    if not valid_email_address(user):
        raise RuntimeError(
            f"GMAIL_ADDRESS tidak valid: "
            f"{user!r}"
        )

    if not valid_email_address(to_email):
        raise RuntimeError(
            f"Alamat email tujuan tidak valid: "
            f"{to_email!r}"
        )

    subject = clean_text(
        subject
    )

    if not subject:
        subject = (
            "Ide landing page untuk bisnis Anda"
        )

    body = clean_text(
        body
    )

    msg = EmailMessage()

    msg["From"] = user
    msg["To"] = to_email
    msg["Subject"] = subject[:120]

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
            msg,
            from_addr=user,
            to_addrs=[to_email],
        )
