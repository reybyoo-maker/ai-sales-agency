from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .config import DAILY_OUTREACH_LIMIT, BATCH_SIZE
from .gemini_agent import analyze_prospect
from .outreach import build_message_body, send_email
from .sheets import get_sheet, rows_as_dicts, update_row


def eligible(row: dict, test_mode: bool) -> bool:
    if str(row.get("opt_out", "")).strip().lower() in {"yes", "true", "1", "stop"}:
        return False

    status = str(row.get("outreach_status", "")).strip().upper()
    allowed = {"", "NEW", "AUDITED"}
    if test_mode:
        allowed.add("ERROR")
    if status not in allowed:
        return False

    # Test mode can audit any usable prospect even if it has no email.
    if test_mode:
        return any(str(row.get(k, "")).strip() for k in ("business_name", "website", "instagram", "phone"))

    # Real automated outreach channel in V1 = email.
    return bool(str(row.get("email", "")).strip())


def main() -> None:
    ws = get_sheet()
    records = rows_as_dicts(ws)

    test_mode = os.getenv("TEST_MODE", "false").strip().lower() == "true"
    today = datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()

    sent_today = sum(
        1
        for r in records
        if str(r.get("outreach_status", "")).upper() == "CONTACTED"
        and str(r.get("outreach_at", "")).startswith(today)
    )
    remaining = max(0, DAILY_OUTREACH_LIMIT - sent_today)
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
            print(f"Processing row {row_number}: {row.get('business_name', '')}")
            result = analyze_prospect(row)

            row["audit_score"] = result.get("score", "")
            row["audit_summary"] = "; ".join(str(x) for x in result.get("observed_gaps", [])[:4])
            row["notes"] = str(result.get("contact_angle", ""))
            row["message_subject"] = str(result.get("subject", "")).strip()
            row["message_body"] = str(result.get("body", "")).strip()

            # Directory/article/review results are stored as audited but not contacted.
            if str(result.get("fit", "")).lower() == "not_a_business_lead":
                row["outreach_status"] = "SKIPPED"
                row["outreach_at"] = datetime.now(timezone.utc).isoformat()
                update_row(ws, row_number, row)
                print("SKIPPED: not an individual business lead")
                continue

            if test_mode:
                row["outreach_status"] = "TESTED"
                row["outreach_at"] = datetime.now(timezone.utc).isoformat()
                update_row(ws, row_number, row)
                print(f"TESTED: score={row['audit_score']} subject={row['message_subject']}")
                continue

            email = str(row.get("email", "")).strip()
            if not email:
                row["outreach_status"] = "NO_EMAIL"
                row["outreach_at"] = datetime.now(timezone.utc).isoformat()
                update_row(ws, row_number, row)
                print("NO_EMAIL: saved for another channel")
                continue

            body = build_message_body(result, row.get("business_name") or "bisnis ini")
            send_email(email, row["message_subject"], body)

            row["message_body"] = body
            row["outreach_status"] = "CONTACTED"
            row["outreach_at"] = datetime.now(timezone.utc).isoformat()
            update_row(ws, row_number, row)
            print(f"SENT: {row.get('business_name')} -> {email}")

        except Exception as exc:
            row["outreach_status"] = "ERROR"
            old = str(row.get("notes", "")).strip()
            err = f"{type(exc).__name__}: {exc}"
            row["notes"] = f"{old} | {err}" if old else err
            update_row(ws, row_number, row)
            print(f"ERROR row {row_number}: {exc}")


if __name__ == "__main__":
    main()
