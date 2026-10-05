from __future__ import annotations

import smtplib
import ssl
import sys
from email.message import EmailMessage

from .config import CANDIDATE_EMAIL, CANDIDATE_WA, CV_PDF_PATH, GMAIL_APP_PASSWORD, GMAIL_ADDRESS
from .sheets import get_ws, records

def send_one(job_id: str) -> None:
    rows = records(get_ws())
    row = next((r for r in rows if str(r.get('job_id', '')).strip() == job_id), None)
    if not row:
        raise RuntimeError(f'job_id tidak ditemukan: {job_id}')
    if str(row.get('status', '')).strip().upper() != 'READY':
        raise RuntimeError('Hanya job berstatus READY yang boleh dikirim.')
    if str(row.get('recipient_email', '')).lower().strip().endswith('@gmail.com') is False:
        raise RuntimeError('Penerima bukan Gmail; pengiriman diblokir.')
    if not CV_PDF_PATH.exists():
        raise RuntimeError(f'CV tidak ditemukan: {CV_PDF_PATH}')
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise RuntimeError('GMAIL_ADDRESS / GMAIL_APP_PASSWORD belum diisi.')

    msg = EmailMessage()
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = row['recipient_email']
    msg['Subject'] = row['subject']
    if CANDIDATE_EMAIL:
        msg['Reply-To'] = CANDIDATE_EMAIL
    msg.set_content(row['body'])
    msg.add_attachment(CV_PDF_PATH.read_bytes(), maintype='application', subtype='pdf', filename=CV_PDF_PATH.name)

    with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as server:
        server.ehlo()
        server.starttls(context=ssl.create_default_context())
        server.ehlo()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)

    print(f'SENT ONE: {row["job_title"]} -> {row["recipient_email"]} | WA {CANDIDATE_WA}')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python -m app.send_single JOB_ID')
    send_one(sys.argv[1])