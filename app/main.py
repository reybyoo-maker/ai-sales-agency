from __future__ import annotations

import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import (
    BATCH_MAX_PROSPECTS,
    DAILY_OUTREACH_LIMIT,
    DISCOVERY_PER_RUN,
    EMAILS_PER_RUN,
    SEND_DELAY_SECONDS,
    TEST_MODE,
    TIMEZONE,
)
from .discovery import discover
from .gemini_batch import create_batch, get_batch, parse_inline_results
from .outreach import build_message, send_email, wa_link
from .sheets import append_prospect, get_ws, records, update

COMPLETED = {
    "JOB_STATE_SUCCEEDED",
    "JOB_STATE_FAILED",
    "JOB_STATE_CANCELLED",
    "JOB_STATE_EXPIRED",
}


def now_iso() -> str:
    return datetime.now(ZoneInfo(TIMEZONE)).isoformat()


def norm(v: str) -> str:
    return (v or "").strip().lower().rstrip("/")


def daily_sent(rows: list[dict]) -> int:
    today = datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()
    return sum(
        1 for r in rows
        if norm(str(r.get("outreach_status", ""))) == "contacted"
        and str(r.get("outreach_at", "")).startswith(today)
    )


def discover_and_append(ws, rows: list[dict]) -> int:
    existing = set()
    for r in rows:
        for field in ("email", "website", "instagram", "phone", "business_name"):
            v = norm(str(r.get(field, "")))
            if v:
                existing.add((field, v))
    try:
        found = discover(limit=DISCOVERY_PER_RUN)
    except Exception as exc:
        print(f"DISCOVERY ERROR: {type(exc).__name__}: {exc}")
        return 0
    added = 0
    for p in found:
        keys = []
        for field in ("email", "website", "instagram", "phone", "business_name"):
            v = norm(str(p.get(field, "")))
            if v:
                keys.append((field, v))
        if any(k in existing for k in keys):
            continue
        try:
            append_prospect(ws, p)
            existing.update(keys)
            added += 1
        except Exception as exc:
            print(f"SHEET APPEND ERROR {p.get('business_name')}: {exc}")
    return added


def find_active_batch(rows: list[dict]):
    queued = []
    for idx, row in enumerate(rows, start=2):
        if norm(str(row.get("outreach_status", ""))) != "ai_queued":
            continue
        notes = str(row.get("notes", ""))
        m = re.search(r"batch_name=([^;|]+)", notes)
        if m:
            queued.append((idx, row, m.group(1).strip()))
    if not queued:
        return None
    job_name = queued[0][2]
    same = [(idx, row) for idx, row, name in queued if name == job_name]
    same.sort(key=lambda x: int(re.search(r"batch_index=(\d+)", str(x[1].get("notes", ""))).group(1)))
    return job_name, same


def submit_batch(ws, rows: list[dict], sent: int) -> None:
    available = DAILY_OUTREACH_LIMIT - sent
    if available <= 0:
        return
    max_items = min(BATCH_MAX_PROSPECTS, 5 if TEST_MODE else BATCH_MAX_PROSPECTS)
    candidates = []
    for idx, row in enumerate(rows, start=2):
        status = norm(str(row.get("outreach_status", "")))
        if status not in {"new", "error"}:
            continue
        if norm(str(row.get("opt_out", ""))) in {"yes", "true", "1", "stop"}:
            continue
        email = str(row.get("email", "")).strip()
        if "@" not in email or "." not in email.split("@")[-1]:
            continue
        candidates.append((idx, row))
        if len(candidates) >= min(max_items, available):
            break

    if not candidates:
        return

    print(f"Submitting Gemini Batch for {len(candidates)} prospects...")
    job = create_batch([row for _, row in candidates], display_name=f"ai-sales-agency-{int(time.time())}")
    job_name = job.name
    for i, (row_number, row) in enumerate(candidates):
        update(
            ws,
            row_number,
            outreach_status="AI_QUEUED",
            notes=f"batch_name={job_name}; batch_index={i}; queued_at={now_iso()}",
        )
    print(f"Batch created: {job_name}")


def poll_batch_and_mark_ready(ws, rows: list[dict]) -> int:
    active = find_active_batch(rows)
    if not active:
        return 0
    job_name, queued = active
    print(f"Checking batch: {job_name}")
    job = get_batch(job_name)
    state = getattr(getattr(job, "state", None), "name", str(getattr(job, "state", "")))
    print(f"Batch state: {state}")
    if state not in COMPLETED:
        return 0
    if state != "JOB_STATE_SUCCEEDED":
        msg = str(getattr(job, "error", "Batch gagal"))[:1200]
        for row_number, _ in queued:
            update(ws, row_number, outreach_status="AI_ERROR", notes=msg)
        return 0

    results = parse_inline_results(job)
    if len(results) != len(queued):
        raise RuntimeError(f"Batch hasil {len(results)} tidak sama dengan queue {len(queued)}")

    for (row_number, row), result in zip(queued, results):
        score = result.get("score", "")
        summary = "; ".join(str(x) for x in (result.get("observed_gaps") or [])[:3])
        body = build_message(str(result.get("body", "")), row.get("business_name") or "bisnis ini")
        link = wa_link(row.get("business_name") or "bisnis ini")
        fit = norm(str(result.get("fit", "")))
        if fit == "not_a_business_lead":
            status = "SKIPPED"
        else:
            status = "READY"
        update(
            ws,
            row_number,
            audit_score=score,
            audit_summary=summary,
            message_subject=str(result.get("subject", "")).strip(),
            message_body=body,
            wa_link=link,
            outreach_status=status,
            outreach_at="",
            notes=str(result.get("contact_angle", "")),
        )
    return len(queued)


def send_ready(ws, rows: list[dict], sent_today: int) -> int:
    if TEST_MODE:
        return 0
    remaining = max(0, DAILY_OUTREACH_LIMIT - sent_today)
    if remaining <= 0:
        return 0
    quota = min(EMAILS_PER_RUN, remaining)
    candidates = []
    for idx, row in enumerate(rows, start=2):
        if norm(str(row.get("outreach_status", ""))) != "ready":
            continue
        email = str(row.get("email", "")).strip().lower()
        if "@" not in email:
            continue
        candidates.append((idx, row))
        if len(candidates) >= quota:
            break

    sent = 0
    for row_number, row in candidates:
        try:
            send_email(
                str(row.get("email", "")).strip(),
                str(row.get("message_subject", "Landing page untuk bisnis Anda")),
                str(row.get("message_body", "")),
            )
            update(ws, row_number, outreach_status="CONTACTED", outreach_at=now_iso())
            sent += 1
            print(f"SENT row {row_number}: {row.get('business_name')} -> {row.get('email')}")
            if sent < len(candidates):
                time.sleep(max(15, SEND_DELAY_SECONDS))
        except Exception as exc:
            update(ws, row_number, outreach_status="ERROR", notes=f"{type(exc).__name__}: {exc}"[:1200])
            print(f"SEND ERROR row {row_number}: {exc}")
    return sent


def main() -> None:
    ws = get_ws()
    rows = records(ws)
    added = discover_and_append(ws, rows)
    rows = records(ws)

    sent = daily_sent(rows)
    print("=== AI SALES AGENCY V1.5 ===")
    print(f"TEST_MODE: {TEST_MODE}")
    print(f"New prospects: {added}")
    print(f"Sent today: {sent}/{DAILY_OUTREACH_LIMIT}")

    # First, finish an existing Gemini batch if any.
    ready_count = poll_batch_and_mark_ready(ws, rows)
    if ready_count:
        rows = records(ws)
        print(f"Batch completed: {ready_count}")

    # If no batch is active, submit the next batch. In TEST_MODE, submit only once
    # so scheduled test runs do not keep creating new Gemini jobs.
    rows = records(ws)
    has_ready = any(norm(str(r.get("outreach_status", ""))) == "ready" for r in rows)
    if not find_active_batch(rows) and daily_sent(rows) < DAILY_OUTREACH_LIMIT:
        if not (TEST_MODE and has_ready):
            submit_batch(ws, rows, daily_sent(rows))

    # Send already prepared email queue. TEST_MODE intentionally sends nothing.
    rows = records(ws)
    sent_now = send_ready(ws, rows, daily_sent(rows))
    print(f"Emails sent this run: {sent_now}")


if __name__ == "__main__":
    main()
