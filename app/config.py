from __future__ import annotations

import os


# ============================================================
# AI
# ============================================================

MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.1-flash-lite",
).strip()


# ============================================================
# PRODUK YANG DIJUAL
# ============================================================

OFFER_NAME = os.getenv(
    "OFFER_NAME",
    "B2B Lead Database",
).strip()

STARTER_PRICE = os.getenv(
    "STARTER_PRICE",
    "299000",
).strip()

SAMPLE_LEADS = int(
    os.getenv(
        "SAMPLE_LEADS",
        "10",
    )
)

TARGET_COUNTRY = os.getenv(
    "TARGET_COUNTRY",
    "Indonesia",
).strip()


# ============================================================
# DISCOVERY
# ============================================================

DISCOVERY_PER_RUN = int(
    os.getenv(
        "DISCOVERY_PER_RUN",
        "30",
    )
)


# ============================================================
# GEMINI
# ============================================================

BATCH_MAX_PROSPECTS = int(
    os.getenv(
        "BATCH_MAX_PROSPECTS",
        "12",
    )
)


# ============================================================
# EMAIL
# ============================================================

EMAILS_PER_RUN = int(
    os.getenv(
        "EMAILS_PER_RUN",
        "10",
    )
)

DAILY_OUTREACH_LIMIT = int(
    os.getenv(
        "DAILY_OUTREACH_LIMIT",
        "20",
    )
)

SEND_DELAY_SECONDS = int(
    os.getenv(
        "SEND_DELAY_SECONDS",
        "60",
    )
)


# ============================================================
# GOOGLE SHEETS
# ============================================================

SHEET_TAB = os.getenv(
    "SHEET_TAB",
    "Prospects",
).strip()


# ============================================================
# MODE AMAN
# ============================================================

# TRUE = jangan kirim email.
# Agent hanya discovery -> AI -> Google Sheet.
#
# Untuk tahap testing, JANGAN diubah ke false.
TEST_MODE = os.getenv(
    "TEST_MODE",
    "true",
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


# ============================================================
# TIMEZONE
# ============================================================

TIMEZONE = os.getenv(
    "TIMEZONE",
    "Asia/Jakarta",
).strip()
