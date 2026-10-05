from __future__ import annotations

import os
import re
import smtplib
import ssl
import unicodedata
from email.message import EmailMessage


def normalize_value(value: str) -> str:
    if not value:
        return ""

    value = unicodedata.normalize("NFKC", str(value))
    value = "".join(value.split())

    return value.strip()


def clean_text(value: str) -> str:
    if not value:
        return ""

    value = unicodedata.normalize("NFKC", str(value))

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
    value = normalize_value(value)

    return re.sub(r"\s+", "", value)


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


def build_message(
    body: str,
    business_name: str,
) -> str:
    """
    Membersihkan body email B2B.
    Tidak menambahkan portfolio atau WhatsApp.
    """

    body = clean_text(body or "")

    if not body:
        body = (
            f"Halo, saya ingin menghubungi tim {business_name} "
            "terkait kebutuhan lead generation."
        )

    return body.strip()


def send_email(
    to_email: str,
    subject: str,
    body: str,
) -> None:

    user = clean_email_address(
        os.getenv("GMAIL_ADDRESS", "")
    )

    password = normalize_value(
        os.getenv("GMAIL_APP_PASSWORD", "")
    )

    to_email = clean_email_address(to_email)

    if not user or not password:
        raise RuntimeError(
            "GMAIL_ADDRESS / GMAIL_APP_PASSWORD belum diisi"
        )

    if not valid_email_address(user):
        raise RuntimeError(
            f"GMAIL_ADDRESS tidak valid: {user!r}"
        )

    if not valid_email_address(to_email):
        raise RuntimeError(
            f"Alamat email tujuan tidak valid: {to_email!r}"
        )

    subject = clean_text(subject)

    if not subject:
        subject = "B2B Lead Database"

    body = clean_text(body)

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
