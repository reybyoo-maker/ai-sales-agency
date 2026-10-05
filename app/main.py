from __future__ import annotations

import csv
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import AI_PROJECT_NOTE, CSV_FIELDS, DATA_FILE, MAX_AI_PER_RUN, TIMEZONE
from .discovery import search_once
from .job_agent import analyze_job, load_cv_text
from .sheets import append_job, get_profile, get_ws

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
    print('BANDUNG JOB HUNTER | DISCOVERY + DRAFT')
    print('========================================')

    rows = load_rows()
    existing = {r.get('job_id', '') for r in rows if r.get('job_id')}
    jobs = search_once()
    print(f'DISCOVERED={len(jobs)}')

    try:
        cv_text = load_cv_text()
    except Exception as exc:
        print(f'CV ERROR: {exc}')
        return

    try:
        profile = get_profile()
    except Exception as exc:
        print(f'PROFILE ERROR: {exc}')
        return

    try:
        ws = get_ws()
    except Exception as exc:
        print(f'SHEETS ERROR: {exc}')
        return

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
            status = 'SIAP_KIRIM' if job.get('recipient_email') else 'WATCHLIST'
            row = {
                **job,
                'candidate_headline': profile.get('headline', ''),
                'ai_project_note': profile.get('ai_project', AI_PROJECT_NOTE),
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
            try:
                append_job(ws, row)
            except Exception as exc:
                print(f'SHEETS APPEND WARNING: {exc}')
            print(f'{status} | score={job.get("prospect_score",0)} | {job["job_title"]} | {job.get("recipient_email","")}')
        except Exception as exc:
            print(f'AI ERROR | {job["job_title"]} | {type(exc).__name__}: {exc}')

    save_rows(rows)
    print(f'NEW_JOBS={added}')
    print('Change status from SIAP_KIRIM to KIRIM in Google Sheets for jobs you want the sender to process at the next peak window.')
    print('========================================')

if __name__ == '__main__':
    main()