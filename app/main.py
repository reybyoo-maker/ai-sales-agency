from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .config import DAILY_OUTREACH_LIMIT, BATCH_SIZE
from .gemini_agent import analyze_batch
from .outreach import build_message_body, send_email, wa_link
from .sheets import get_sheet, rows_as_dicts, update_row


TEST_MODE = os.getenv("TEST_MODE", "false").strip().lower() == "true"


def eligible(row: dict) -> bool:
    if str(row.get("opt_out", "")).strip().lower() in {"yes", "true", "1", "stop"}:
        return False

    status = str(row.get("outreach_status", "")).strip().upper()
    allowed = {"", "NEW", "AUDITED", "ERROR"}
    return status in allowed and any(
        str(row.get(k, "")).strip()
        for k in ("business_name", "website", "instagram", "phone")
    )


def today_contacted(records: list[dict]) -> int:
    today = datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
    return sum(
        1
        for r in records
        if str(r.get("outreach_status", "")).upper() == "CONTACTED"
        and str(r.get("outreach_at", "")).startswith(today)
    )


def apply_result(row: dict, result: dict) -> None:
    row["audit_score"] = result.get("score", "")
    row["audit_summary"] = "; ".join(
        str(x) for x in (result.get("observed_gaps") or [])[:4]
    )
    row["notes"] = str(result.get("contact_angle", ""))
    row["message_subject"] = str(result.get("subject", "")).strip()
    row["message_body"] = str(result.get("body", "")).strip()
    row["wa_link"] = wa_link(
        f"Halo Rey, saya dari {row.get('business_name') or 'bisnis ini'}. "
        "Saya tertarik dengan landing page dan ingin lihat detailnya."
    )


def main() -> None:
    ws = get_sheet()
    records = rows_as_dicts(ws)

    sent_today = today_contacted(records)
    remaining = max(0, DAILY_OUTREACH_LIMIT - sent_today)
    if remaining <= 0:
        print("Daily outreach limit reached.")
        return

    # BATCH_SIZE is now the number of prospects sent in ONE Gemini request.
    batch_size = min(BATCH_SIZE, remaining)
    candidates = [
        (idx + 2, row)
        for idx, row in enumerate(records)
        if eligible(row)
    ][:batch_size]

    print(f"Candidates: {len(candidates)}")
    print(f"Gemini batch size: {len(candidates)}")
    print(f"TEST_MODE: {TEST_MODE}")

    if not candidates:
        print("No eligible prospect found.")
        return

    rows = [row for _, row in candidates]

    try:
        results = analyze_batch(rows)
    except Exception as exc:
        message = str(exc)
        print(f"Gemini batch ERROR: {type(exc).__name__}: {message}")
        for row_number, row in candidates:
            old = str(row.get("notes", "")).strip()
            row["outreach_status"] = "AI_QUOTA_WAIT" if "GenerateRequestsPerDay" in message else "ERROR"
            row["notes"] = f"{old} | {type(exc).__name__}: {message}" if old else f"{type(exc).__name__}: {message}"
            update_row(ws, row_number, row)
        return

    if len(results) != len(candidates):
        raise RuntimeError(
            f"Gemini returned {len(results)} results for {len(candidates)} prospects"
        )

    for (row_number, row), result in zip(candidates, results):
        try:
            apply_result(row, result)

            if str(result.get("fit", "")).lower() == "not_a_business_lead":
                row["outreach_status"] = "SKIPPED"
                row["outreach_at"] = datetime.now(timezone.utc).isoformat()
                update_row(ws, row_number, row)
                print(f"SKIPPED row {row_number}: not a business lead")
                continue

            if TEST_MODE:
                row["outreach_status"] = "TESTED"
                row["outreach_at"] = datetime.now(timezone.utc).isoformat()
                row["message_body"] = build_message_body(
                    result, row.get("business_name") or "bisnis ini"
                )
                update_row(ws, row_number, row)
                print(f"TESTED row {row_number}: score={row.get('audit_score')}")
                continue

            email = str(row.get("email", "")).strip()
            if not email:
                row["outreach_status"] = "NO_EMAIL"
                row["outreach_at"] = datetime.now(timezone.utc).isoformat()
                update_row(ws, row_number, row)
                print(f"NO_EMAIL row {row_number}")
                continue

            body = build_message_body(result, row.get("business_name") or "bisnis ini")
            send_email(email, row.get("message_subject", "Landing page"), body)
            row["message_body"] = body
            row["outreach_status"] = "CONTACTED"
            row["outreach_at"] = datetime.now(timezone.utc).isoformat()
            update_row(ws, row_number, row)
            print(f"SENT row {row_number}: {row.get('business_name')} -> {email}")

        except Exception as exc:
            old = str(row.get("notes", "")).strip()
            err = f"{type(exc).__name__}: {exc}"
            row["outreach_status"] = "ERROR"
            row["notes"] = f"{old} | {err}" if old else err
            update_row(ws, row_number, row)
            print(f"ERROR row {row_number}: {err}")


if __name__ == "__main__":
    main()
