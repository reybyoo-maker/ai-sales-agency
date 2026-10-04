from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .config import DAILY_OUTREACH_LIMIT, BATCH_SIZE
from .gemini_agent import audit_prospect, make_outreach
from .outreach import build_message_body, send_email
from .sheets import get_sheet, rows_as_dicts, update_row


def eligible(row: dict, test_mode: bool) -> bool:
    """Select rows for this run.

    In test mode, rows without email can still be audited and used to generate
    a draft message. ERROR rows are retried in test mode so failed test runs
    can recover after a code fix.

    In real mode, email is currently required because email is the automated
    cold-outreach channel implemented in V1.
    """
    if str(row.get("opt_out", "")).strip().lower() in {
        "yes", "true", "1", "stop"
    }:
        return False

    status = str(row.get("outreach_status", "")).strip().upper()

    allowed = {"", "NEW", "AUDITED"}
    if test_mode:
        allowed.add("ERROR")

    if status not in allowed:
        return False

    if test_mode:
        return any(
            str(row.get(field, "")).strip()
            for field in ("business_name", "website", "instagram", "phone")
        )

    return bool(str(row.get("email", "")).strip())


def main() -> None:
    ws = get_sheet()
    records = rows_as_dicts(ws)

    test_mode = os.getenv("TEST_MODE", "false").strip().lower() == "true"
    now_local = datetime.now(ZoneInfo("Asia/Jakarta"))
    local_today = now_local.date().isoformat()

    total_sent_today = sum(
        1
        for r in records
        if str(r.get("outreach_status", "")).strip().upper() == "CONTACTED"
        and str(r.get("outreach_at", "")).startswith(local_today)
    )

    remaining = max(0, DAILY_OUTREACH_LIMIT - total_sent_today)
    if remaining <= 0:
        print("Daily outreach limit reached.")
        return

    candidates = [
        (idx + 2, row)
        for idx, row in enumerate(records)
        if eligible(row, test_mode)
    ]
    batch = candidates[: min(BATCH_SIZE, remaining)]

    print(f"Candidates: {len(candidates)}")
    print(f"Processing: {len(batch)}")
    print(f"TEST_MODE: {test_mode}")

    for row_number, row in batch:
        try:
            print("=" * 60)
            print(f"Processing row {row_number}")
            print(f"Business: {row.get('business_name', '')}")
            print(f"Email: {row.get('email', '') or '(none)'}")

            if not str(row.get("audit_score", "")).strip():
                audit = audit_prospect(row)
                row["audit_score"] = audit.get("score", "")

                gaps = audit.get("observed_gaps", [])
                if isinstance(gaps, list):
                    row["audit_summary"] = "; ".join(
                        str(x) for x in gaps[:3]
                    )
                else:
                    row["audit_summary"] = str(gaps)

                row["notes"] = str(audit.get("contact_angle", ""))

            generated = make_outreach(row)
            subject = str(generated.get("subject", "")).strip()
            body = build_message_body(
                generated,
                row.get("business_name") or "bisnis ini",
            )

            row["message_subject"] = subject
            row["message_body"] = body

            if test_mode:
                row["outreach_status"] = "TESTED"
                row["outreach_at"] = datetime.now(timezone.utc).isoformat()
                update_row(ws, row_number, row)
                print("TEST MODE: no email sent.")
                print(f"Audit score: {row.get('audit_score', '')}")
                print(f"Subject: {subject}")
                continue

            email = str(row.get("email", "")).strip()
            if not email:
                row["outreach_status"] = "NO_EMAIL"
                row["outreach_at"] = datetime.now(timezone.utc).isoformat()
                update_row(ws, row_number, row)
                print("Skipped real send: no email.")
                continue

            send_email(email, subject, body)

            row["outreach_status"] = "CONTACTED"
            row["outreach_at"] = datetime.now(timezone.utc).isoformat()
            row["wa_link"] = body.split(
                "Lanjut via WhatsApp: ", 1
            )[-1].strip()
            update_row(ws, row_number, row)
            print(f"SENT: {row.get('business_name')} -> {email}")

        except Exception as exc:
            row["outreach_status"] = "ERROR"
            old_notes = str(row.get("notes", "")).strip()
            error_text = f"{type(exc).__name__}: {exc}"
            row["notes"] = (
                f"{old_notes} | {error_text}"
                if old_notes
                else error_text
            )
            update_row(ws, row_number, row)
            print(f"ERROR row {row_number}: {exc}")


if __name__ == "__main__":
    main()
