from __future__ import annotations

import csv
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import AI_PROJECT_NOTE, CSV_FIELDS, DATA_FILE, MAX_AI_PER_RUN, TIMEZONE
from .discovery import search_once
from .job_agent import analyze_job, load_cv_text
from .sheets import append_job, get_profile, get_ws, records, update_row_by_job_id

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
    print('BANDUNG JOB HUNTER | DISCOVERY + AI DRAFT')
    print('========================================')

    ws = get_ws()
    profile = get_profile()
    sheet_rows = records(ws)
    rows = load_rows()

    existing = {str(r.get('job_id', '')).strip() for r in sheet_rows + rows if r.get('job_id')}
    existing_urls = {
        str(r.get('source_url', '')).strip().split('#', 1)[0].split('?', 1)[0].rstrip('/').lower()
        for r in sheet_rows + rows
        if r.get('source_url')
    }
    jobs = search_once()
    new_jobs = []

    for job in jobs:
        source_url_key = str(job.get('source_url', '')).strip().split('#', 1)[0].split('?', 1)[0].rstrip('/').lower()
        if job['job_id'] in existing or (source_url_key and source_url_key in existing_urls):
            continue
        row = {
            **job,
            'found_at': now_iso(),
            'candidate_headline': profile.get('headline', ''),
            'ai_project_note': profile.get('ai_project', AI_PROJECT_NOTE),
            'subject': '',
            'body': '',
            'flyer_summary': '',
            'status': 'BARU',
            'sent_at': '',
            'send_error': '',
        }
        rows.append(row)
        new_jobs.append(row)
        existing.add(job['job_id'])
        if source_url_key:
            existing_urls.add(source_url_key)
        try:
            append_job(ws, row)
        except Exception as exc:
            print(f'SHEETS APPEND ERROR | {job["job_id"]} | {exc}')

    print(f'DISCOVERED={len(jobs)} NEW={len(new_jobs)}')
    save_rows(rows)

    try:
        cv_text = load_cv_text()
    except Exception as exc:
        print(f'CV WARNING: {exc}')
        print('Jobs are still stored in Sheets. Set CV_PDF_BASE64, then rerun.')
        return

    # Draft new and previously undrafted rows; discovery is never blocked by CV errors.
    # Google Sheets is the source of truth for AI drafting. The local CSV
    # may contain stale rows from earlier runs that were removed or replaced.
    current_sheet_rows = records(ws)
    candidates = [
        r for r in current_sheet_rows
        if (r.get('recipient_email') or r.get('company_tier') == 'famous' or r.get('flyer_image_urls'))
        and not str(r.get('subject', '')).strip()
    ][:MAX_AI_PER_RUN]

    drafted = 0
    for job in candidates:
        try:
            result = analyze_job(job, cv_text, profile)
            flyer_gmail = str(result.get('gmail_application_email', '')).strip().lower()
            if flyer_gmail.endswith('@gmail.com') and not job.get('recipient_email'):
                job['recipient_email'] = flyer_gmail
            status = 'SIAP_REVIEW' if job.get('recipient_email') else 'WATCHLIST'
            update_row_by_job_id(
                ws, job['job_id'],
                candidate_headline=profile.get('headline', ''),
                ai_project_note=profile.get('ai_project', AI_PROJECT_NOTE),
                subject=str(result.get('subject', '')).strip(),
                body=str(result.get('body', '')).strip(),
                flyer_summary=str(result.get('flyer_summary', '')).strip(),
                recipient_email=job.get('recipient_email', ''),
                application_method='GMAIL' if job.get('recipient_email') else job.get('application_method', ''),
                status=status,
            )
            job['candidate_headline'] = profile.get('headline', '')
            job['ai_project_note'] = profile.get('ai_project', AI_PROJECT_NOTE)
            job['subject'] = str(result.get('subject', '')).strip()
            job['body'] = str(result.get('body', '')).strip()
            job['flyer_summary'] = str(result.get('flyer_summary', '')).strip()
            job['application_method'] = 'GMAIL' if job.get('recipient_email') else job.get('application_method', '')
            job['status'] = status
            drafted += 1
            print(f'DRAFTED | score={job.get("prospect_score",0)} | {job.get("job_title")} | {job.get("recipient_email","")}')
        except Exception as exc:
            print(f'AI DRAFT ERROR | {job.get("job_title")} | {type(exc).__name__}: {exc}')

    save_rows(rows)
    print(f'DRAFTED={drafted}')
    print('Manual control: change Sheet status SIAP_REVIEW -> KIRIM for the rows you want sent.')
    print('========================================')

if __name__ == '__main__':
    main()