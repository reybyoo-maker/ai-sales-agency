from __future__ import annotations

import json
import os
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = [
    "job_id", "job_title", "company", "category", "work_mode", "location",
    "source_url", "published_date", "deadline_date", "recipient_email",
    "fit_score", "fit_reason", "subject", "body", "status", "send_approved",
    "discovered_at", "sent_at", "error", "notes",
]

def get_ws():
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    tab = os.getenv("SHEET_TAB", "Job Applications").strip()
    if not raw or not sheet_id:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON / GOOGLE_SHEET_ID belum diisi")

    creds = Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    sh = gspread.authorize(creds).open_by_key(sheet_id)

    try:
        ws = sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab, rows=5000, cols=len(HEADERS))

    current = [str(x).strip() for x in ws.row_values(1)]
    if not current:
        ws.append_row(HEADERS, value_input_option="USER_ENTERED")
    else:
        for header in HEADERS:
            if header not in current:
                ws.update_cell(1, len(current) + 1, header)
                current.append(header)
    return ws

def records(ws) -> list[dict[str, Any]]:
    return ws.get_all_records()

def append_job(ws, job: dict[str, Any]) -> None:
    headers = [str(x).strip() for x in ws.row_values(1)]
    ws.append_row([job.get(h, "") for h in headers], value_input_option="USER_ENTERED")
