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
    "business_name",
    "niche",
    "city",
    "province",
    "website",
    "email",
    "phone",
    "source_url",
    "website_title",
    "website_text",
    "intent_type",
    "intent_source",
    "intent_url",
    "intent_title",
    "intent_date",
    "intent_budget",
    "intent_score",
    "audit_score",
    "audit_summary",
    "outreach_status",
    "outreach_at",
    "message_subject",
    "message_body",
    "send_approved",
    "opt_out",
    "notes",
    "instagram",
    "wa_link",
]


def get_ws():
    raw = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "",
    ).strip()

    sheet_id = os.getenv(
        "GOOGLE_SHEET_ID",
        "",
    ).strip()

    tab = os.getenv(
        "SHEET_TAB",
        "Prospects",
    ).strip()

    if not raw or not sheet_id:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON / "
            "GOOGLE_SHEET_ID belum diisi"
        )

    try:
        service_account = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON bukan JSON valid"
        ) from exc

    creds = Credentials.from_service_account_info(
        service_account,
        scopes=SCOPES,
    )

    gc = gspread.authorize(creds)

    sh = gc.open_by_key(
        sheet_id
    )

    try:
        ws = sh.worksheet(tab)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(
            title=tab,
            rows=5000,
            cols=len(HEADERS),
        )

    values = ws.get_all_values()

    # Sheet baru / kosong.
    if not values:
        ws.append_row(
            HEADERS,
            value_input_option="USER_ENTERED",
        )
        return ws

    current_headers = [
        str(header).strip()
        for header in values[0]
    ]

    # Tambahkan header yang belum ada
    # ke sebelah kanan. Tidak menghapus kolom
    # lama yang sudah dimiliki user.
    missing = [
        header
        for header in HEADERS
        if header not in current_headers
    ]

    if missing:
        for header in missing:
            ws.update_cell(
                1,
                len(current_headers) + 1,
                header,
            )
            current_headers.append(header)

    return ws


def records(ws):
    return ws.get_all_records()


def append_prospect(
    ws,
    prospect: dict[str, Any],
) -> None:
    headers = [
        str(header).strip()
        for header in ws.row_values(1)
    ]

    row = [
        prospect.get(
            header,
            "",
        )
        for header in headers
    ]

    # Semua prospect baru mulai sebagai NEW.
    if "outreach_status" in headers:
        row[
            headers.index("outreach_status")
        ] = "NEW"

    ws.append_row(
        row,
        value_input_option="USER_ENTERED",
    )


def update(
    ws,
    row_number: int,
    **fields,
) -> None:
    headers = [
        str(header).strip()
        for header in ws.row_values(1)
    ]

    for key, value in fields.items():

        if key not in headers:
            continue

        column = (
            headers.index(key) + 1
        )

        ws.update_cell(
            row_number,
            column,
            value,
        )
