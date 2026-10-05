from __future__ import annotations

import json
import os
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]

HEADERS = [
    'job_id', 'found_at', 'published_date', 'deadline_date', 'age_days',
    'job_title', 'company', 'company_tier', 'category', 'work_mode', 'location',
    'source_url', 'flyer_image_urls', 'source_domain', 'application_method', 'recipient_email',
    'prospect_score', 'score_reason', 'candidate_headline', 'ai_project_note',
    'subject', 'body', 'flyer_summary', 'status', 'sent_at', 'send_error', 'notes',
]

PROFILE_HEADERS = ['key', 'value']

def _connect():
    raw = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '').strip()
    sheet_id = os.getenv('GOOGLE_SHEET_ID', '').strip()
    if not raw or not sheet_id:
        raise RuntimeError('GOOGLE_SERVICE_ACCOUNT_JSON / GOOGLE_SHEET_ID belum diisi')
    creds = Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(sheet_id)

def get_profile_ws():
    sh = _connect()
    tab = os.getenv('PROFILE_TAB', 'Candidate Profile').strip()
    try:
        ws = sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab, rows=20, cols=2)
    if not ws.row_values(1):
        ws.append_row(PROFILE_HEADERS, value_input_option='USER_ENTERED')
        defaults = [
            ['candidate_name', 'REYNALDI KURNIA SONJAYA'],
            ['headline', 'Leader | Mentor | Marketing Officer | Data Analyst | Digital Marketing | Promotion | Influencer'],
            ['email', 'reybyoo@gmail.com'],
            ['whatsapp', '6287813871926'],
            ['ai_project', 'Saat ini saya juga mengembangkan project Agent Agency AI untuk membantu pekerjaan menjadi lebih mudah, terstruktur, dan efisien.'],
        ]
        for row in defaults:
            ws.append_row(row, value_input_option='USER_ENTERED')
    return ws

def get_profile() -> dict[str, str]:
    ws = get_profile_ws()
    values = ws.get_all_values()
    if not values:
        return {}
    headers = [str(x).strip() for x in values[0]]
    if "candidate_name" in headers and "headline" in headers:
        row = values[1] if len(values) > 1 else []
        return {
            headers[i]: str(row[i]).strip() if i < len(row) else ""
            for i in range(len(headers))
        }
    rows = ws.get_all_records()
    return {
        str(r.get('key', '')).strip(): str(r.get('value', '')).strip()
        for r in rows
        if r.get('key')
    }

def get_ws():
    sh = _connect()
    tab = os.getenv('SHEET_TAB', 'Job Applications').strip()
    try:
        ws = sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab, rows=10000, cols=len(HEADERS))
    current = [str(x).strip() for x in ws.row_values(1)]
    if not current:
        ws.append_row(HEADERS, value_input_option='USER_ENTERED')
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
    ws.append_row([job.get(h, '') for h in headers], value_input_option='USER_ENTERED')

def append_jobs(ws, jobs: list[dict[str, Any]]) -> None:
    if not jobs:
        return
    headers = [str(x).strip() for x in ws.row_values(1)]
    values = [[job.get(h, '') for h in headers] for job in jobs]
    ws.append_rows(values, value_input_option='USER_ENTERED')

def update_row_by_job_id(ws, job_id: str, **fields: Any) -> None:
    values = ws.get_all_values()
    if not values:
        raise RuntimeError('Sheet kosong')
    headers = [str(x).strip() for x in values[0]]
    try:
        idx = headers.index('job_id')
    except ValueError:
        raise RuntimeError('Kolom job_id tidak ditemukan')
    for row_num, row in enumerate(values[1:], start=2):
        if len(row) > idx and str(row[idx]).strip() == job_id:
            updates = []
            for key, value in fields.items():
                if key not in headers:
                    continue
                col_num = headers.index(key) + 1
                # One range per field, submitted in a single Sheets API batch request.
                updates.append({
                    "range": f"{gspread.utils.rowcol_to_a1(row_num, col_num)}",
                    "values": [[value]],
                })
            if updates:
                for attempt in range(3):
                    try:
                        ws.batch_update(updates)
                        break
                    except gspread.exceptions.APIError as exc:
                        if "429" not in str(exc) or attempt == 2:
                            raise
                        import time
                        time.sleep(2 * (attempt + 1))
            return
    raise RuntimeError(f'job_id tidak ditemukan: {job_id}')