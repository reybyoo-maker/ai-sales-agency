from __future__ import annotations

import os

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()

PORTFOLIO_URL = os.getenv(
    "PORTFOLIO_URL",
    "https://reynaldi-sonjaya.lynk.id/p/Reylandingpage",
).strip()

# PRODUKSI
DAILY_OUTREACH_LIMIT = int(
    os.getenv("DAILY_OUTREACH_LIMIT", "100")
)

DISCOVERY_PER_RUN = int(
    os.getenv("DISCOVERY_PER_RUN", "30")
)

# Jumlah yang diproses AI setiap workflow.
BATCH_MAX_PROSPECTS = int(
    os.getenv("BATCH_MAX_PROSPECTS", "12")
)

# Jumlah email maksimal per workflow.
EMAILS_PER_RUN = int(
    os.getenv("EMAILS_PER_RUN", "12")
)

# Jeda antar email.
SEND_DELAY_SECONDS = int(
    os.getenv("SEND_DELAY_SECONDS", "60")
)

SHEET_TAB = os.getenv(
    "SHEET_TAB",
    "Prospects"
)

# PRODUKSI: email benar-benar dikirim.
TEST_MODE = False

TIMEZONE = os.getenv(
    "TIMEZONE",
    "Asia/Jakarta"
)
