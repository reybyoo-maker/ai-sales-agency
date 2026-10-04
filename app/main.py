from __future__ import annotations

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
from .gemini_batch import generate_prospect
from .outreach import build_message, send_email, wa_link
from .sheets import append_prospect, get_ws, records, update


def now_iso() -> str:
    return datetime.now(ZoneInfo(TIMEZONE)).isoformat()


def norm(v: str) -> str:
    return (v or "").strip().lower().rstrip("/")


def daily_sent(rows: list[dict]) -> int:
    today = datetime.now(ZoneInfo(TIMEZONE)).date().isoformat()

    return sum(
        1
        for r in rows
        if norm(str(r.get("outreach_status", ""))) == "contacted"
        and str(r.get("outreach_at", "")).startswith(today)
    )


def discover_and_append(ws, rows: list[dict]) -> int:
    existing = set()

    # Identitas kuat untuk deduplication.
    for r in rows:
        for field in (
            "email",
            "website",
            "instagram",
            "phone",
        ):
            v = norm(str(r.get(field, "")))
            if v:
                existing.add((field, v))

    try:
        found = discover(limit=DISCOVERY_PER_RUN)

        print(f"Discovery returned: {len(found)} prospects")

    except Exception as exc:
        print(
            f"DISCOVERY ERROR: "
            f"{type(exc).__name__}: {exc}"
        )
        return 0

    added = 0
    skipped = 0

    for p in found:
        business_name = str(
            p.get("business_name", "")
        ).strip()

        keys = []

        for field in (
            "email",
            "website",
            "instagram",
            "phone",
        ):
            v = norm(str(p.get(field, "")))

            if v:
                keys.append((field, v))

        duplicate_keys = [
            k for k in keys
            if k in existing
        ]

        if duplicate_keys:
            skipped += 1

            print(
                f"SKIP DUPLICATE: "
                f"{business_name} | "
                f"{duplicate_keys}"
            )

            continue

        try:
            append_prospect(ws, p)

            existing.update(keys)

            added += 1

            print(
                f"ADDED: {business_name}"
            )

        except Exception as exc:
            print(
                f"SHEET APPEND ERROR "
                f"{business_name}: {exc}"
            )

    print(
        f"Discovery summary: "
        f"found={len(found)}, "
        f"added={added}, "
        f"duplicate={skipped}"
    )

    return added


def submit_batch(ws, rows: list[dict], sent: int) -> int:
    """
    Nama fungsi tetap 'submit_batch' agar struktur project lama
    tidak perlu berubah banyak.

    Sekarang fungsi ini TIDAK membuat Gemini Batch API.
    Setiap prospect diproses langsung dengan generate_content().
    """

    available = DAILY_OUTREACH_LIMIT - sent

    if available <= 0:
        print("Daily outreach limit reached.")
        return 0

    max_items = min(
        BATCH_MAX_PROSPECTS,
        5 if TEST_MODE else BATCH_MAX_PROSPECTS,
    )

    candidates = []

    for idx, row in enumerate(rows, start=2):
        status = norm(str(row.get("outreach_status", "")))

        if status not in {
            "new",
            "error",
            "ai_queued",
            "ai_error",
        }:
            continue

        if norm(str(row.get("opt_out", ""))) in {
            "yes",
            "true",
            "1",
            "stop",
        }:
            continue

        email = str(row.get("email", "")).strip()

        if "@" not in email:
            continue

        if "." not in email.split("@")[-1]:
            continue

        candidates.append((idx, row))

        if len(candidates) >= min(max_items, available):
            break

    if not candidates:
        print("No AI candidates found.")
        return 0

    print(
        f"Processing Gemini directly for "
        f"{len(candidates)} prospects..."
    )

    processed = 0

    for i, (row_number, row) in enumerate(candidates):
        business_name = (
            str(row.get("business_name", "")).strip()
            or "bisnis ini"
        )

        print(
            f"[{i + 1}/{len(candidates)}] "
            f"Analyzing: {business_name}"
        )

        try:
            # Tandai sedang diproses.
            update(
                ws,
                row_number,
                outreach_status="AI_PROCESSING",
                notes=f"ai_started_at={now_iso()}",
            )

            result = generate_prospect(row)

            score = result.get("score", "")

            summary = "; ".join(
                str(x)
                for x in (result.get("observed_gaps") or [])[:3]
            )

            body = build_message(
                str(result.get("body", "")),
                business_name,
            )

            link = wa_link(business_name)

            fit = norm(
                str(result.get("fit", ""))
            )

            if fit == "not_a_business_lead":
                status = "SKIPPED"
            else:
                status = "READY"

            update(
                ws,
                row_number,
                audit_score=score,
                audit_summary=summary,
                message_subject=str(
                    result.get(
                        "subject",
                        "Landing page untuk bisnis Anda",
                    )
                ).strip(),
                message_body=body,
                wa_link=link,
                outreach_status=status,
                outreach_at="",
                notes=str(
                    result.get("contact_angle", "")
                ).strip(),
            )

            processed += 1

            print(
                f"OK row {row_number}: "
                f"{business_name} -> {status}"
            )

        except Exception as exc:
            error_message = (
                f"{type(exc).__name__}: {exc}"
            )[:1200]

            update(
                ws,
                row_number,
                outreach_status="ERROR",
                notes=error_message,
            )

            print(
                f"AI ERROR row {row_number}: "
                f"{error_message}"
            )

        # Jeda agar request tidak ditembak terlalu cepat.
        if i < len(candidates) - 1:
            time.sleep(
                max(1, SEND_DELAY_SECONDS)
                if SEND_DELAY_SECONDS > 0
                else 1
            )

    print(
        f"Gemini processing completed: "
        f"{processed}/{len(candidates)}"
    )

    return processed


def send_ready(
    ws,
    rows: list[dict],
    sent_today: int,
) -> int:

    if TEST_MODE:
        print("TEST_MODE=True -> email sending disabled.")
        return 0

    remaining = max(
        0,
        DAILY_OUTREACH_LIMIT - sent_today,
    )

    if remaining <= 0:
        return 0

    quota = min(
        EMAILS_PER_RUN,
        remaining,
    )

    candidates = []

    for idx, row in enumerate(rows, start=2):
        if norm(
            str(row.get("outreach_status", ""))
        ) != "ready":
            continue

        email = (
            str(row.get("email", ""))
            .strip()
            .lower()
        )

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
                str(
                    row.get(
                        "message_subject",
                        "Landing page untuk bisnis Anda",
                    )
                ),
                str(
                    row.get(
                        "message_body",
                        "",
                    )
                ),
            )

            update(
                ws,
                row_number,
                outreach_status="CONTACTED",
                outreach_at=now_iso(),
            )

            sent += 1

            print(
                f"SENT row {row_number}: "
                f"{row.get('business_name')} "
                f"-> {row.get('email')}"
            )

            if sent < len(candidates):
                time.sleep(
                    max(15, SEND_DELAY_SECONDS)
                )

        except Exception as exc:
            error_message = (
                f"{type(exc).__name__}: {exc}"
            )[:1200]

            update(
                ws,
                row_number,
                outreach_status="ERROR",
                notes=error_message,
            )

            print(
                f"SEND ERROR row {row_number}: "
                f"{error_message}"
            )

    return sent


def main() -> None:
    ws = get_ws()

    rows = records(ws)

    added = discover_and_append(
        ws,
        rows,
    )

    rows = records(ws)

    sent = daily_sent(rows)

    print("=== AI SALES AGENCY V1.6 ===")
    print(f"TEST_MODE: {TEST_MODE}")
    print(f"New prospects: {added}")
    print(
        f"Sent today: "
        f"{sent}/{DAILY_OUTREACH_LIMIT}"
    )

    # Process prospect dengan Gemini secara langsung.
    rows = records(ws)

    processed = submit_batch(
        ws,
        rows,
        sent,
    )

    if processed:
        rows = records(ws)

    # Kirim email yang sudah READY.
    sent_now = send_ready(
        ws,
        rows,
        daily_sent(rows),
    )

    print(
        f"Emails sent this run: {sent_now}"
    )


if __name__ == "__main__":
    main()
