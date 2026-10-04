from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .config import DAILY_OUTREACH_LIMIT, BATCH_SIZE
from .gemini_agent import audit_prospect, make_outreach
from .outreach import build_message_body, send_email
from .sheets import get_sheet, rows_as_dicts, update_row


def eligible(row: dict) -> bool:
    if str(row.get("opt_out", "")).strip().lower() in {
        "yes",
        "true",
        "1",
        "stop",
    }:
        return False

    status = str(row.get("outreach_status", "")).strip().upper()

    if status not in {"", "NEW", "AUDITED"}:
        return False

    if not str(row.get("email", "")).strip():
        return False

    return True


def main():
    ws = get_sheet()
    records = rows_as_dicts(ws)

    test_mode = os.getenv("TEST_MODE", "false").strip().lower() == "true"

    local_today = datetime.now(
        ZoneInfo("Asia/Jakarta")
    ).date().isoformat()

    total_sent_today = sum(
        1
        for r in records
        if str(r.get("outreach_status", "")).upper() == "CONTACTED"
        and str(r.get("outreach_at", "")).startswith(local_today)
    )

    remaining = max(0, DAILY_OUTREACH_LIMIT - total_sent_today)

    if remaining <= 0:
        print("Daily outreach limit reached.")
        return

    candidates = [
        (idx + 2, r)
        for idx, r in enumerate(records)
        if eligible(r)
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
            print(f"Email: {row.get('email', '')}")

            # -------------------------------------------------
            # 1. AUDIT PROSPECT
            # -------------------------------------------------
            if not row.get("audit_score"):
                audit = audit_prospect(row)

                row["audit_score"] = audit.get("score", "")

                observed_gaps = audit.get(
                    "observed_gaps",
                    []
                )

                if isinstance(observed_gaps, list):
                    row["audit_summary"] = "; ".join(
                        str(x) for x in observed_gaps[:3]
                    )
                else:
                    row["audit_summary"] = str(observed_gaps)

                row["notes"] = str(
                    audit.get("contact_angle", "")
                )

                update_row(ws, row_number, row)

                print(
                    f"Audit score: {row['audit_score']}"
                )

            # -------------------------------------------------
            # 2. GENERATE PERSONALIZED MESSAGE
            # -------------------------------------------------
            generated = make_outreach(row)

            body = build_message_body(
                generated,
                row.get("business_name") or "bisnis ini",
            )

            row["message_subject"] = str(
                generated.get("subject", "")
            ).strip()

            row["message_body"] = body

            # -------------------------------------------------
            # 3. TEST MODE
            # -------------------------------------------------
            if test_mode:
                row["outreach_status"] = "TESTED"
                row["outreach_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                update_row(ws, row_number, row)

                print("TEST MODE: email NOT sent.")
                print(
                    f"Subject: {row['message_subject']}"
                )
                continue

            # -------------------------------------------------
            # 4. REAL SEND
            # -------------------------------------------------
            send_email(
                row["email"].strip(),
                row["message_subject"],
                body,
            )

            row["outreach_status"] = "CONTACTED"
            row["outreach_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            update_row(ws, row_number, row)

            print(
                f"SENT: {row.get('business_name')} "
                f"-> {row.get('email')}"
            )

        except Exception as exc:
            row["outreach_status"] = "ERROR"

            old_notes = str(
                row.get("notes", "")
            ).strip()

            error_text = (
                f"{type(exc).__name__}: {exc}"
            )

            row["notes"] = (
                f"{old_notes} | {error_text}"
                if old_notes
                else error_text
            )

            update_row(ws, row_number, row)

            print(
                f"ERROR row {row_number}: {exc}"
            )


if __name__ == "__main__":
    main()
