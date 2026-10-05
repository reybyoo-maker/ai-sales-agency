from __future__ import annotations

import hashlib
import re
import time
from urllib.parse import urlparse

from ddgs import DDGS

from .web import clean_email, clean_phone, snapshot


# ============================================================
# TARGET INTENT
# ============================================================

INTENT_QUERIES = [
    '"B2B lead generation" "looking for"',
    '"B2B lead generation" "need"',
    '"email list building" "looking for"',
    '"email list building" "need"',
    '"B2B leads" "looking for"',
    '"B2B leads" "need"',
    '"lead research" "looking for"',
    '"lead research" "need"',
    '"prospect research" "looking for"',
    '"prospect research" "need"',
    '"data enrichment" "looking for"',
    '"data enrichment" "need"',
    '"appointment setting" "looking for"',
    '"appointment setting" "need"',
    '"lead researcher" "hiring"',
    '"lead generation specialist" "hiring"',
    'site:upwork.com/freelance-jobs/ "B2B Lead Generation"',
    'site:upwork.com/freelance-jobs/ "Email List Building"',
    'site:upwork.com/freelance-jobs/ "Lead Research"',
    'site:freelancer.com/projects/ "B2B Lead Generation"',
    'site:freelancer.com/projects/ "Email List"',
    'site:freelancer.com/projects/ "Lead Generation"',
    'site:guru.com/jobs/ "Lead Generation"',
    'site:guru.com/jobs/ "Email List"',
    'site:onlinejobs.ph/jobseekers/job/ "Lead Generation"',
    'site:onlinejobs.ph/jobseekers/job/ "Email Outreach"',
]


# ============================================================
# DOMAIN YANG TIDAK KITA ANGGAP SEBAGAI WEBSITE BISNIS
# ============================================================

BLOCKED_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "wikipedia.org",
    "pinterest.com",
    "reddit.com",
    "quora.com",
}


BAD_TITLES = (
    "directory",
    "direktori",
    "review",
    "reviews",
    "ranking",
    "top 10",
    "top 20",
    "best ",
    "rekomendasi",
)


BAD_PATHS = (
    "/directory",
    "/direktori",
    "/category/",
    "/kategori/",
    "/tag/",
    "/search",
)


# ============================================================
# HELPER
# ============================================================

def normalize(value: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        value or "",
    ).strip()


def domain(url: str) -> str:
    try:
        return (
            urlparse(url)
            .netloc
            .lower()
            .split(":")[0]
            .removeprefix("www.")
        )
    except Exception:
        return ""


def is_blocked(url: str) -> bool:
    current = domain(url)

    if not current:
        return True

    return any(
        current == blocked
        or current.endswith("." + blocked)
        for blocked in BLOCKED_DOMAINS
    )


def extract_email(text: str) -> str:
    if not text:
        return ""

    match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text,
    )

    if not match:
        return ""

    return clean_email(
        match.group(0)
    )


def extract_phone(text: str) -> str:
    if not text:
        return ""

    match = re.search(
        r"(?:\+62|62|0)(?:[\s().-]*\d){9,14}",
        text,
    )

    if not match:
        return ""

    return clean_phone(
        match.group(0)
    )


def intent_score(
    title: str,
    snippet: str,
    query: str,
) -> int:

    text = (
        f"{title} "
        f"{snippet} "
        f"{query}"
    ).lower()

    score = 50

    strong_signals = (
        "we need",
        "need ",
        "looking for",
        "hiring",
        "hire",
        "seeking",
        "required",
        "requirement",
        "urgent",
    )

    service_signals = (
        "b2b lead",
        "lead generation",
        "lead research",
        "email list",
        "email list building",
        "prospect research",
        "data enrichment",
        "appointment setting",
        "lead researcher",
        "sales research",
        "outreach",
    )

    if any(
        signal in text
        for signal in strong_signals
    ):
        score += 20

    matching_services = sum(
        1
        for signal in service_signals
        if signal in text
    )

    score += min(
        matching_services * 5,
        25,
    )

    if (
        "upwork.com" in text
        or "freelancer.com" in text
        or "guru.com" in text
        or "onlinejobs.ph" in text
    ):
        score += 5

    return min(
        score,
        100,
    )


def fingerprint(prospect: dict) -> str:
    raw = "|".join(
        str(
            prospect.get(field, "")
        )
        .strip()
        .lower()
        .rstrip("/")
        for field in (
            "business_name",
            "website",
            "email",
            "intent_url",
            "intent_title",
        )
    )

    return hashlib.sha1(
        raw.encode("utf-8")
    ).hexdigest()


# ============================================================
# DISCOVERY
# ============================================================

def discover(limit: int = 30) -> list[dict]:

    if limit <= 0:
        return []

    # Rotasi query setiap 30 menit supaya
    # workflow otomatis tidak terus mencari query sama.
    window = int(
        time.time() // 1800
    )

    query_count = min(
        20,
        len(INTENT_QUERIES),
    )

    start = (
        window * query_count
    ) % len(INTENT_QUERIES)

    selected_queries = [
        INTENT_QUERIES[
            (start + index)
            % len(INTENT_QUERIES)
        ]
        for index in range(query_count)
    ]

    print(
        "========================================"
    )
    print(
        "INTENT DISCOVERY"
    )
    print(
        f"Query count: {len(selected_queries)}"
    )
    print(
        "========================================"
    )

    results_out: list[dict] = []
    seen: set[str] = set()

    with DDGS() as ddgs:

        for query_index, query in enumerate(
            selected_queries,
            start=1,
        ):

            print(
                f"\n[Intent {query_index}/"
                f"{len(selected_queries)}]"
            )

            print(
                f"SEARCH: {query}"
            )

            try:

                search_results = ddgs.text(
                    query,
                    max_results=10,
                )

            except Exception as exc:

                print(
                    "SEARCH ERROR: "
                    f"{type(exc).__name__}: {exc}"
                )

                continue

            for item in search_results or []:

                title = normalize(
                    item.get(
                        "title",
                        "",
                    )
                )

                href = normalize(
                    item.get(
                        "href",
                        "",
                    )
                )

                snippet = normalize(
                    item.get(
                        "body",
                        "",
                    )
                )

                if not href:
                    continue

                if is_blocked(href):
                    continue

                title_lower = title.lower()

                if any(
                    bad in title_lower
                    for bad in BAD_TITLES
                ):
                    continue

                path = urlparse(
                    href
                ).path.lower()

                if any(
                    bad in path
                    for bad in BAD_PATHS
                ):
                    continue

                score = intent_score(
                    title,
                    snippet,
                    query,
                )

                # Untuk tahap pertama kita simpan
                # hanya intent yang cukup kuat.
                if score < 65:
                    continue

                # Ambil halaman untuk mencari
                # email bisnis publik bila ada.
                email = extract_email(
                    snippet
                )

                phone = extract_phone(
                    snippet
                )

                website_title = title
                website_text = ""

                try:

                    snap = snapshot(
                        href
                    )

                    if snap.get("ok"):

                        website_title = normalize(
                            snap.get(
                                "title",
                                "",
                            )
                            or title
                        )

                        website_text = normalize(
                            snap.get(
                                "text",
                                "",
                            )
                        )[:5000]

                        if not email:

                            emails = (
                                snap.get(
                                    "emails"
                                )
                                or []
                            )

                            if emails:
                                email = emails[0]

                        if not phone:

                            phones = (
                                snap.get(
                                    "phones"
                                )
                                or []
                            )

                            if phones:
                                phone = phones[0]

                except Exception as exc:

                    print(
                        "SNAPSHOT WARNING: "
                        f"{href} | "
                        f"{type(exc).__name__}: {exc}"
                    )

                email = clean_email(
                    email
                )

                phone = clean_phone(
                    phone
                )

                # Untuk intent source yang merupakan
                # job marketplace, jangan menganggap
                # judul job sebagai nama perusahaan.
                #
                # Jika website/title belum menunjukkan
                # nama perusahaan, kita simpan title
                # sebagai identifier sementara.
                business_name = (
                    website_title
                    or title
                    or "Unknown Buyer"
                )

                item = {
                    "business_name": business_name,
                    "niche": "B2B Lead Generation",
                    "city": "",
                    "province": "",
                    "website": href,
                    "instagram": "",
                    "email": email,
                    "phone": phone,
                    "source_url": href,

                    # Field intent tetap dikembalikan
                    # walaupun sementara Sheet lama
                    # belum punya kolom terpisah.
                    "intent_type": "B2B Lead Generation",
                    "intent_source": domain(href),
                    "intent_url": href,
                    "intent_title": title,
                    "intent_date": "",
                    "intent_budget": "",
                    "intent_score": score,

                    "website_title": website_title,
                    "website_text": website_text,

                    "audit_score": "",
                    "audit_summary": "",
                    "outreach_status": (
                        "NEW"
                        if email
                        else "NO_EMAIL"
                    ),
                    "outreach_at": "",
                    "wa_link": "",
                    "message_subject": "",
                    "message_body": "",
                    "email_opt_in": "",
                    "opt_out": "",

                    "notes": (
                        "INTENT DISCOVERY | "
                        f"query={query} | "
                        f"intent_score={score} | "
                        f"title={title} | "
                        f"snippet={snippet[:700]}"
                    ),
                }

                fp = fingerprint(
                    item
                )

                if fp in seen:
                    continue

                seen.add(fp)
                results_out.append(
                    item
                )

                print(
                    "FOUND INTENT: "
                    f"{title} | "
                    f"score={score} | "
                    f"email={email or 'NO EMAIL'}"
                )

                if (
                    len(results_out)
                    >= limit
                ):
                    print(
                        f"\nIntent target reached: {limit}"
                    )
                    return results_out

    print(
        "\n========================================"
    )
    print(
        "INTENT DISCOVERY FINISHED"
    )
    print(
        f"Valid intent prospects: "
        f"{len(results_out)}"
    )
    print(
        "========================================"
    )

    return results_out
