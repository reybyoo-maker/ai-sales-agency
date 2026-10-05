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
from .outreach import build_message, send_email
from .sheets import append_prospect, get_ws, records, update


def now_iso() -> str:
    return datetime.now(
        ZoneInfo(TIMEZONE)
    ).isoformat()


def norm(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
        .rstrip("/")
    )


def daily_sent(rows: list[dict]) -> int:
    today = datetime.now(
        ZoneInfo(TIMEZONE)
    ).date().isoformat()

    return sum(
        1
        for row in rows
        if norm(
            row.get(
                "outreach_status",
                "",
            )
        ) == "contacted"
        and str(
            row.get(
                "outreach_at",
                "",
            )
        ).startswith(today)
    )


def is_opted_out(row: dict) -> bool:
    return norm(
        row.get(
            "opt_out",
            "",
        )
    ) in {
        "yes",
        "true",
        "1",
        "stop",
    }


def discover_and_append(
    ws,
    rows: list[dict],
) -> int:
    existing_keys: set[tuple[str, str]] = set()

    for row in rows:
        for field in (
            "email",
            "website",
            "source_url",
            "intent_url",
        ):
            value = norm(
                row.get(
                    field,
                    "",
                )
            )

            if value:
                existing_keys.add(
                    (field, value)
                )

    try:
        found = discover(
            limit=DISCOVERY_PER_RUN
        )

        print(
            f"Discovery returned: "
            f"{len(found)} prospects"
        )

    except Exception as exc:
        print(
            "DISCOVERY ERROR: "
            f"{type(exc).__name__}: {exc}"
        )
        return 0

    added = 0
    skipped = 0

    for prospect in found:
        business_name = (
            str(
                prospect.get(
                    "business_name",
                    "",
                )
            ).strip()
            or "Unknown Buyer"
        )

        keys = []

        for field in (
            "email",
            "website",
            "source_url",
            "intent_url",
        ):
            value = norm(
                prospect.get(
                    field,
                    "",
                )
            )

            if value:
                keys.append(
                    (field, value)
                )

        duplicate_keys = [
            key
            for key in keys
            if key in existing_keys
        ]

        if duplicate_keys:
            skipped += 1

            print(
                "SKIP DUPLICATE: "
                f"{business_name} | "
                f"{duplicate_keys}"
            )

            continue

        try:
            append_prospect(
                ws,
                prospect,
            )

            existing_keys.update(
                keys
            )

            added += 1

            print(
                "ADDED: "
                f"{business_name} | "
                f"email={prospect.get('email', '') or 'NO EMAIL'} | "
                f"intent={prospect.get('intent_type', '')}"
            )

        except Exception as exc:
            print(
                "SHEET APPEND ERROR "
                f"{business_name}: "
                f"{type(exc).__name__}: {exc}"
            )

    print(
        "Discovery summary: "
        f"found={len(found)}, "
        f"added={added}, "
        f"duplicate={skipped}"
    )

    return added


def process_ai(
    ws,
    rows: list[dict],
) -> int:
    candidates: list[tuple[int, dict]] = []

    max_items = max(
        1,
        BATCH_MAX_PROSPECTS,
    )

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        status = norm(
            row.get(
                "outreach_status",
                "",
            )
        )

        if status not in {
            "new",
            "error",
        }:
            continue

        if is_opted_out(row):
            continue

        email = str(
            row.get(
                "email",
                "",
            )
        ).strip()

        if (
            "@" not in email
            or "." not in email.rsplit("@", 1)[-1]
        ):
            continue

        candidates.append(
            (
                row_number,
                row,
            )
        )

        if len(candidates) >= max_items:
            break

    if not candidates:
        print(
            "No AI candidates found."
        )
        return 0

    print(
        "Processing Gemini for "
        f"{len(candidates)} prospects..."
    )

    processed = 0

    for index, (
        row_number,
        row,
    ) in enumerate(
        candidates,
        start=1,
    ):
        business_name = (
            str(
                row.get(
                    "business_name",
                    "",
                )
            ).strip()
            or "Unknown Buyer"
        )

        print(
            f"[AI {index}/{len(candidates)}] "
            f"{business_name}"
        )

        try:
            update(
                ws,
                row_number,
                outreach_status="AI_PROCESSING",
                notes=(
                    f"AI started "
                    f"{now_iso()}"
                ),
            )

            result = generate_prospect(
                row
            )

            fit = norm(
                result.get(
                    "fit",
                    "",
                )
            )

            score = result.get(
                "score",
                "",
            )

            reasons = (
                result.get(
                    "observed_gaps",
                    [],
                )
                or []
            )

            summary = "; ".join(
                str(item)
                for item in reasons[:4]
            )

            subject = (
                str(
                    result.get(
                        "subject",
                        "",
                    )
                ).strip()
            )

            body = build_message(
                str(
                    result.get(
                        "body",
                        "",
                    )
                ),
                business_name,
            )

            contact_angle = str(
                result.get(
                    "contact_angle",
                    "",
                )
            ).strip()

            if fit == "not_a_business_lead":
                status = "SKIPPED"
            else:
                status = "READY"

            update(
                ws,
                row_number,
                intent_score=(
                    row.get(
                        "intent_score",
                        "",
                    )
                ),
                audit_score=score,
                audit_summary=summary,
                outreach_status=status,
                outreach_at="",
                message_subject=subject,
                message_body=body,
                notes=(
                    contact_angle
                    or summary
                ),
            )

            processed += 1

            print(
                f"AI OK row={row_number} "
                f"score={score} "
                f"status={status}"
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
                "AI ERROR "
                f"row={row_number}: "
                f"{error_message}"
            )

    print(
        "Gemini processing completed: "
        f"{processed}/{len(candidates)}"
    )

    return processed


def send_ready(
    ws,
    rows: list[dict],
    sent_today: int,
) -> int:
    if TEST_MODE:
        print(
            "TEST_MODE=true -> "
            "email sending disabled."
        )
        return 0

    remaining = max(
        0,
        DAILY_OUTREACH_LIMIT - sent_today,
    )

    if remaining <= 0:
        print(
            "Daily outreach limit reached."
        )
        return 0

    quota = min(
        EMAILS_PER_RUN,
        remaining,
    )

    candidates: list[tuple[int, dict]] = []

    for row_number, row in enumerate(
        rows,
        start=2,
    ):
        if norm(
            row.get(
                "outreach_status",
                "",
            )
        ) != "ready":
            continue

        if is_opted_out(row):
            continue

        approval = norm(
            row.get(
                "send_approved",
                "",
            )
        )

        if approval not in {
            "yes",
            "true",
            "1",
        }:
            continue

        email = str(
            row.get(
                "email",
                "",
            )
        ).strip()

        if (
            "@" not in email
            or "." not in email.rsplit("@", 1)[-1]
        ):
            continue

        candidates.append(
            (
                row_number,
                row,
            )
        )

        if len(candidates) >= quota:
            break

    if not candidates:
        print(
            "No approved READY prospects."
        )
        return 0

    print(
        f"Sending {len(candidates)} "
        "approved emails..."
    )

    sent = 0

    for index, (
        row_number,
        row,
    ) in enumerate(
        candidates,
        start=1,
    ):
        try:
            send_email(
                str(
                    row.get(
                        "email",
                        "",
                    )
                ).strip(),
                str(
                    row.get(
                        "message_subject",
                        "B2B lead database",
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
                f"SENT {index}/"
                f"{len(candidates)}: "
                f"{row.get('business_name')} -> "
                f"{row.get('email')}"
            )

            if (
                index < len(candidates)
                and SEND_DELAY_SECONDS > 0
            ):
                time.sleep(
                    SEND_DELAY_SECONDS
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
                f"SEND ERROR row "
                f"{row_number}: "
                f"{error_message}"
            )

    return sent


def main() -> None:
    print(
        "========================================"
    )
    print(
        "AI SALES AGENCY — B2B LEAD DATABASE"
    )
    print(
        "========================================"
    )

    print(
        f"TEST_MODE: {TEST_MODE}"
    )

    ws = get_ws()

    rows = records(ws)

    added = discover_and_append(
        ws,
        rows,
    )

    print(
        f"New prospects added: {added}"
    )

    rows = records(ws)

    processed = process_ai(
        ws,
        rows,
    )

    print(
        f"AI processed: {processed}"
    )

    rows = records(ws)

    sent = send_ready(
        ws,
        rows,
        daily_sent(rows),
    )

    print(
        f"Emails sent: {sent}"
    )

    print(
        "========================================"
    )
    print(
        "RUN COMPLETE"
    )
    print(
        "========================================"
    )


if __name__ == "__main__":
    main()
