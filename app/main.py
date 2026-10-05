from __future__ import annotations

import csv
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import AI_PROJECT_NOTE, CANDIDATE_HEADLINE, CSV_FIELDS, DATA_FILE, MAX_AI_PER_RUN, MIN_FIT_SCORE, TIMEZONE
from .discovery import search_once
from .job_agent import analyze_job, load_cv_text
from .sheets import append_job, get_profile, get_ws, records

def now_iso() -> str:
    return datetime.now(ZoneInfo(TIMEZONE)).isoformat()

def load_rows() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def save_rows(rows: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

def main() -> None:
    print('========================================')
    print('BANDUNG JOB HUNTER | CV MATCH + QUEUE')
    print('========================================')

    rows = load_rows()
    existing = {r.get('job_id', '') for r in rows if r.get('job_id')}
    jobs = search_once()
    print(f'DISCOVERED={len(jobs)}')

    try:
        cv_text = load_cv_text()
        profile = get_profile()
    except Exception as exc:
        print(f'CV ERROR: {exc}')
        return

    ws = None
    if get_ws:
        try:
            ws = get_ws()
        except Exception as exc:
            print(f'SHEETS WARNING: {exc}')

    processed = 0
    added = 0
    for job in jobs:
        if job['job_id'] in existing:
            continue
        if processed >= MAX_AI_PER_RUN:
            break
        processed += 1

        try:
            result = analyze_job(job, cv_text, profile)
            score = int(result.get('fit_score', 0) or 0)
            status = 'READY' if score >= MIN_FIT_SCORE and job.get('recipient_email') else ('READY_NO_GMAIL' if score >= MIN_FIT_SCORE else 'REJECTED_FIT')
            row = {
                **job,
                'fit_score': score,
                'fit_reason': str(result.get('fit_reason', '')).strip(),
                'subject': str(result.get('subject', '')).strip(),
                'body': str(result.get('body', '')).strip(),
                'status': status,
                'send_approved': 'NO',
                'discovered_at': now_iso(),
                'sent_at': '',
                'error': '',
            }
            rows.append(row)
            existing.add(job['job_id'])
            added += 1
            if ws:
                try:
                    append_job(ws, row)
                except Exception as exc:
                    print(f'SHEETS APPEND WARNING: {exc}')
            print(f'{status} | {score} | {job["job_title"]} | {job["recipient_email"]}')
        except Exception as exc:
            print(f'AI ERROR | {job["job_title"]} | {type(exc).__name__}: {exc}')

    save_rows(rows)
    print(f'QUEUED={added}')
    print('NO MASS AUTO-SEND: review READY rows in Google Sheets before sending.')
    print('========================================')

if __name__ == '__main__':
    main()