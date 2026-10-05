from __future__ import annotations

import base64
import csv
import re
import smtplib
import ssl
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import CV_PDF_BASE64, CV_PDF_PATH, DAILY_SEND_LIMIT, DATA_FILE, GMAIL_ADDRESS, GMAIL_APP_PASSWORD, MAX_SEND_PER_RUN, SEND_DELAY_SECONDS, TIMEZONE
from .sheets import get_profile, get_ws, records, update_row_by_job_id

def now_iso() -> str:
    return datetime.now(ZoneInfo(TIMEZONE)).isoformat()

def prepare_cv() -> Path:
    if CV_PDF_BASE64:
        CV_PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
        CV_PDF_PATH.write_bytes(base64.b64decode(CV_PDF_BASE64))
    if not CV_PDF_PATH.exists() or CV_PDF_PATH.stat().st_size < 1000:
        raise RuntimeError(f'CV PDF tidak ditemukan/invalid: {CV_PDF_PATH}')
    return CV_PDF_PATH

def daily_sent(rows: list[dict]) -> int:
    today = datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()
    return sum(1 for r in rows if str(r.get('status','')).strip().upper() == 'TERKIRIM' and str(r.get('sent_at','')).startswith(today))

def send_row(row: dict, profile: dict[str, str], cv_path: Path) -> None:
    recipient = str(row.get('recipient_email','')).strip().lower()
    if not recipient.endswith('@gmail.com'):
        raise RuntimeError('Penerima bukan Gmail; baris ini tidak dikirim via email.')
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise RuntimeError('GMAIL_ADDRESS / GMAIL_APP_PASSWORD belum diset.')

    msg = EmailMessage()
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = recipient
    msg['Subject'] = str(row.get('subject','')).strip()[:180]
    msg['Reply-To'] = profile.get('email') or GMAIL_ADDRESS
    msg.set_content(str(row.get('body','')).strip())
    msg.add_attachment(cv_path.read_bytes(), maintype='application', subtype='pdf', filename=cv_path.name)

    with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)

def main() -> None:
    ws = get_ws()
    profile = get_profile()
    cv_path = prepare_cv()
    rows = records(ws)
    already_sent = daily_sent(rows)
    quota = min(MAX_SEND_PER_RUN, max(0, DAILY_SEND_LIMIT - already_sent))
    print(f'PEAK SENDER | quota={quota} | already_sent_today={already_sent}')
    if quota <= 0:
        return

    sent = 0
    for row in rows:
        if sent >= quota:
            break
        if str(row.get('status','')).strip().upper() != 'KIRIM':
            continue
        job_id = str(row.get('job_id','')).strip()
        recipient = str(row.get('recipient_email','')).strip().lower()
        if not job_id:
            continue
        if row.get('sent_at'):
            update_row_by_job_id(ws, job_id, status='TERKIRIM')
            continue
        if not recipient.endswith('@gmail.com'):
            update_row_by_job_id(ws, job_id, status='WATCHLIST', send_error='Tidak ada Gmail penerima; gunakan portal/ATS.')
            continue
        if not str(row.get('subject','')).strip() or not str(row.get('body','')).strip():
            update_row_by_job_id(ws, job_id, status='ERROR', send_error='Subject/body AI belum tersedia.')
            continue
        try:
            send_row(row, profile, cv_path)
            update_row_by_job_id(ws, job_id, status='TERKIRIM', sent_at=now_iso(), send_error='')
            sent += 1
            print(f'SENT {sent}/{quota} | {row.get("job_title")} | {row.get("recipient_email")}')
            if sent < quota and SEND_DELAY_SECONDS > 0:
                time.sleep(SEND_DELAY_SECONDS)
        except Exception as exc:
            update_row_by_job_id(ws, job_id, status='ERROR', send_error=f'{type(exc).__name__}: {exc}'[:1000])
            print(f'SEND ERROR | {job_id} | {exc}')

    print(f'SENT_THIS_RUN={sent}')

if __name__ == '__main__':
    main()