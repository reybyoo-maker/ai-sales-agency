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
    "business_name", "niche", "city", "province", "website", "instagram", "email", "phone",
    "source_url", "audit_score", "audit_summary", "outreach_status", "outreach_at", "wa_link",
    "message_subject", "message_body", "notes", "opt_out",
]


def get_ws():
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    tab = os.getenv("SHEET_TAB", "Prospects")
    if not raw or not sheet_id:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON / GOOGLE_SHEET_ID belum diisi")
    creds = Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab, rows=5000, cols=len(HEADERS))
    values = ws.get_all_values()
    if not values:
        ws.append_row(HEADERS, value_input_option="USER_ENTERED")
    else:
        current = values[0]
        missing = [h for h in HEADERS if h not in current]
        if missing:
            raise RuntimeError("Header Google Sheet kurang: " + ", ".join(missing))
    return ws


def records(ws):
    return ws.get_all_records()


def append_prospect(ws, p: dict[str, Any]) -> None:
    row = [p.get(h, "") for h in HEADERS]
    row[11] = "NEW"
    ws.append_row(row, value_input_option="USER_ENTERED")


def update(ws, row_number: int, **fields) -> None:
    headers = ws.row_values(1)
    for key, value in fields.items():
        if key not in headers:
            continue
        col = headers.index(key) + 1
        ws.update_cell(row_number, col, value)
