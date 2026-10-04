from __future__ import annotations
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .config import DAILY_OUTREACH_LIMIT, BATCH_SIZE
from .gemini_agent import audit_prospect, make_outreach
from .outreach import build_message_body, send_email
from .sheets import get_sheet, rows_as_dicts, update_row, HEADERS


def eligible(row: dict) -> bool:
    if str(row.get('opt_out','')).strip().lower() in {'yes','true','1','stop'}:
        return False
    if str(row.get('outreach_status','')).strip().upper() not in {'', 'NEW', 'AUDITED'}:
        return False
    if not str(row.get('email','')).strip():
        return False
    return True


def main():
    ws = get_sheet()
    records = rows_as_dicts(ws)
    local_today = datetime.now(ZoneInfo('Asia/Jakarta')).date().isoformat()
    total_sent_today = sum(1 for r in records if str(r.get('outreach_status','')).upper() == 'CONTACTED' and str(r.get('outreach_at','')).startswith(local_today))
    remaining = max(0, DAILY_OUTREACH_LIMIT - total_sent_today)
    if remaining <= 0:
        print('Daily limit reached.')
        return

    candidates = [(idx + 2, r) for idx, r in enumerate(records) if eligible(r)]
    batch = candidates[:min(BATCH_SIZE, remaining)]
    print(f'Candidates: {len(candidates)} | Sending: {len(batch)}')

    for row_number, row in batch:
        try:
            if not row.get('audit_score'):
                audit = audit_prospect(row)
                row['audit_score'] = audit.get('score', '')
                row['audit_summary'] = '; '.join(audit.get('observed_gaps', [])[:3])
                row['notes'] = audit.get('contact_angle', '')
                update_row(ws, row_number, row)

            generated = make_outreach(row)
            body = build_message_body(generated, row.get('business_name') or 'bisnis saya')
            send_email(row['email'].strip(), generated['subject'].strip(), body)
            row['message_subject'] = generated['subject'].strip()
            row['message_body'] = body
            row['outreach_status'] = 'CONTACTED'
            row['outreach_at'] = datetime.now(timezone.utc).isoformat()
            row['wa_link'] = body.split('Lanjut via WhatsApp: ',1)[-1].strip()
            update_row(ws, row_number, row)
            print(f"SENT: {row.get('business_name')} -> {row.get('email')}")
        except Exception as exc:
            row['outreach_status'] = 'ERROR'
            row['notes'] = f'{row.get("notes", "")} | {type(exc).__name__}: {exc}'.strip(' |')
            update_row(ws, row_number, row)
            print(f"ERROR row {row_number}: {exc}")


if __name__ == '__main__':
    main()
