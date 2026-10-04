from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

HEADERS = [
    'business_name','niche','city','province','website','instagram','email','phone',
    'source_url','audit_score','audit_summary','outreach_status','outreach_at',
    'wa_link','message_subject','message_body','notes','opt_out'
]


def get_client():
    raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not raw:
        raise RuntimeError('GOOGLE_SERVICE_ACCOUNT_JSON is missing')
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def get_sheet():
    sid = os.environ.get('GOOGLE_SHEET_ID')
    if not sid:
        raise RuntimeError('GOOGLE_SHEET_ID is missing')
    sh = get_client().open_by_key(sid)
    try:
        ws = sh.worksheet('Prospects')
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title='Prospects', rows=2000, cols=len(HEADERS))
        ws.append_row(HEADERS)
    if not ws.row_values(1):
        ws.append_row(HEADERS)
    return ws


def rows_as_dicts(ws) -> List[Dict[str, Any]]:
    records = ws.get_all_records()
    return records


def update_row(ws, row_number: int, row: Dict[str, Any]):
    values = [row.get(h, '') for h in HEADERS]
    ws.update(f'A{row_number}:R{row_number}', [values])


def append_rows(ws, rows: List[Dict[str, Any]]):
    if rows:
        ws.append_rows([[r.get(h,'') for h in HEADERS] for r in rows])
