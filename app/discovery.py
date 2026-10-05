from __future__ import annotations

import hashlib
import re
import time
from urllib.parse import urlparse

from ddgs import DDGS

from .web import clean_email, clean_phone, snapshot


# ============================================================
# INTENT QUERIES
# ============================================================

INTENT_QUERIES = [
    'site:upwork.com/freelance-jobs/ "B2B Lead Generation"',
    'site:upwork.com/freelance-jobs/ "Lead Research"',
    'site:upwork.com/freelance-jobs/ "Email List Building"',
    'site:upwork.com/freelance-jobs/ "Prospect Research"',
    'site:upwork.com/freelance-jobs/ "Data Enrichment"',
    'site:upwork.com/freelance-jobs/ "Appointment Setting"',

    'site:freelancer.com/projects/ "B2B Lead Generation"',
    'site:freelancer.com/projects/ "Lead Generation"',
    'site:freelancer.com/projects/ "Email List"',
    'site:freelancer.com/projects/ "Prospect Research"',
    'site:freelancer.com/projects/ "Lead Research"',

    'site:guru.com/jobs/ "Lead Generation"',
    'site:guru.com/jobs/ "Email List"',
    'site:guru.com/jobs/ "Lead Research"',
    'site:guru.com/jobs/ "Appointment Setting"',

    'site:onlinejobs.ph/jobseekers/job/ "Lead Generation"',
    'site:onlinejobs.ph/jobseekers/job/ "Email Outreach"',
    'site:onlinejobs.ph/jobseekers/job/ "Lead Research"',
    'site:onlinejobs.ph/jobseekers/job/ "B2B Lead Generation"',
    'site:onlinejobs.ph/jobseekers/job/ "Appointment Setting"',
]


# ============================================================
# JOB PLATFORM
# ============================================================

JOB_DOMAINS = {
    "upwork.com",
    "freelancer.com",
    "guru.com",
    "onlinejobs.ph",
}


# ============================================================
# WEBSITE YANG TIDAK BOLEH DIANGGAP WEBSITE CLIENT
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

    "upwork.com",
    "freelancer.com",
    "guru.com",
    "onlinejobs.ph",

    "trustpilot.com",
    "grokipedia.com",
}


# ============================================================
# EMAIL YANG TIDAK BOLEH DIPAKAI
# ============================================================

BLOCKED_EMAIL_DOMAINS = {
    "onlinejobs.ph",
    "trustpilot.com",
    "upwork.com",
    "freelancer.com",
    "guru.com",

    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",

    "google.com",

    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "icloud.com",
    "proton.me",
    "protonmail.com",
}


BLOCKED_EMAIL_PREFIXES = (
    "support@",
    "noreply@",
    "no-reply@",
    "donotreply@",
    "do-not-reply@",
)


# ============================================================
# BAD TITLES
# ============================================================

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
    "how to",
    "what is ",
    "guide to",
    "strategies",
    "strategy",
    "tips ",
    "tutorial",
)


# ============================================================
# BAD PATH
# ============================================================

BAD_PATHS = (
    "/directory",
    "/direktori",
    "/category/",
    "/kategori/",
    "/tag/",
    "/search",
    "/blog/",
    "/article/",
    "/articles/",
    "/resources/",
)


# ============================================================
# LIMIT RESOLUTION
# ============================================================

MAX_COMPANY_RESOLUTION_PER_RUN = 8


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


def is_job_domain(url: str) -> bool:
    current = domain(url)

    return any(
        current == item
        or current.endswith("." + item)
        for item in JOB_DOMAINS
    )


def is_blocked(url: str) -> bool:
    current = domain(url)

    if not current:
        return True

    return any(
        current == blocked
        or current.endswith("." + blocked)
        for blocked in BLOCKED_DOMAINS
    )


def is_blocked_email(email: str) -> bool:
    email = clean_email(
        str(email or "")
    ).lower()

    if not email:
        return True

    if "@" not in email:
        return True

    local_part, email_domain = email.rsplit(
        "@",
        1,
    )

    if not local_part:
        return True

    if not email_domain:
        return True

    if email_domain in BLOCKED_EMAIL_DOMAINS:
        return True

    if any(
        email.startswith(prefix)
        for prefix in BLOCKED_EMAIL_PREFIXES
    ):
        return True

    return False


def extract_email(text: str) -> str:
    if not text:
        return ""

    matches = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text,
    )

    for match in matches:
        email = clean_email(match)

        if not email:
            continue

        if is_blocked_email(email):
            continue

        return email

    return ""


def extract_email_from_list(emails) -> str:
    if not emails:
        return ""

    for raw_email in emails:
        email = clean_email(
            str(raw_email or "")
        )

        if not email:
            continue

        if is_blocked_email(email):
            continue

        return email

    return ""


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


# ============================================================
# COMPANY NAME
# ============================================================

def company_name_score(
    name: str,
) -> int:

    name = normalize(name)

    if not name:
        return 0

    low = name.lower()

    bad_exact = {
        "we",
        "we are",
        "we're",
        "company",
        "employer",
        "client",
        "business",
        "agency",
        "team",
        "job",
        "upwork",
        "freelancer",
        "onlinejobs",
        "guru",
        "the company",
        "the employer",
    }

    if low in bad_exact:
        return 0

    # Nama yang jelas-jelas berupa kalimat.
    if len(name) > 70:
        return 0

    if name.endswith(
        (
            ".",
            ",",
            ":",
            ";",
        )
    ):
        return 0

    # Buang kandidat yang terlalu banyak kata.
    words = name.split()

    if len(words) > 8:
        return 0

    score = 50

    if len(name) >= 4:
        score += 10

    if 1 <= len(words) <= 6:
        score += 10

    business_suffixes = (
        "llc",
        "ltd",
        "inc",
        "corp",
        "corporation",
        "group",
        "agency",
        "media",
        "solutions",
        "company",
        "enterprise",
        "studio",
        "digital",
        "marketing",
        "consulting",
        "technologies",
        "technology",
        "systems",
        "services",
        "partners",
    )

    for suffix in business_suffixes:

        if (
            low.endswith(" " + suffix)
            or low == suffix
        ):
            score += 30
            break

    # Nama satu kata yang umum biasanya bukan nama perusahaan.
    if len(words) == 1:
        score -= 20

    return max(
        0,
        min(
            score,
            100,
        ),
    )


def clean_company_candidate(
    name: str,
) -> str:

    name = normalize(name)

    if not name:
        return ""

    # Potong tanda baca di ujung.
    name = name.strip(
        " \t\r\n.,:;|-"
    )

    # Hilangkan awalan yang sering ikut tertangkap.
    prefixes = (
        "about ",
        "company ",
        "company info ",
        "employer ",
        "client ",
    )

    low = name.lower()

    for prefix in prefixes:

        if low.startswith(prefix):
            name = name[
                len(prefix):
            ].strip()

            break

    return name


def extract_company_candidates(
    text: str,
    job_title: str,
) -> list[str]:

    if not text:
        return []

    candidates: list[str] = []

    # --------------------------------------------------------
    # Penting:
    # TIDAK menggunakan re.IGNORECASE.
    # Kita sengaja mempertahankan kapitalisasi asli.
    # --------------------------------------------------------

    patterns = [

        # About Yelico Group
        r"\bAbout\s+"
        r"([A-Z][A-Za-z0-9&.'\-]*(?:"
        r"\s+[A-Z][A-Za-z0-9&.'\-]*"
        r"){0,5})",

        # Company Info: Yelico Group
        r"\bCompany(?: Info| Information)?"
        r"\s*[:\-]\s*"
        r"([A-Z][A-Za-z0-9&.'\-]*(?:"
        r"\s+[A-Z][A-Za-z0-9&.'\-]*"
        r"){0,5})",

        # Employer: Yelico Group
        r"\bEmployer"
        r"\s*[:\-]\s*"
        r"([A-Z][A-Za-z0-9&.'\-]*(?:"
        r"\s+[A-Z][A-Za-z0-9&.'\-]*"
        r"){0,5})",

        # Company: Yelico Group
        r"\bCompany"
        r"\s*[:\-]\s*"
        r"([A-Z][A-Za-z0-9&.'\-]*(?:"
        r"\s+[A-Z][A-Za-z0-9&.'\-]*"
        r"){0,5})",

        # Yelico Group Pay:
        r"\b([A-Z][A-Za-z0-9&.'\-]*(?:"
        r"\s+[A-Z][A-Za-z0-9&.'\-]*"
        r"){0,7})"
        r"\s+Pay\s*[:\-]",

        # Yelico Group is...
        r"\b([A-Z][A-Za-z0-9&.'\-]*(?:"
        r"\s+[A-Z][A-Za-z0-9&.'\-]*"
        r"){0,5})"
        r"\s+(?:is|are|provides|offers|operates|builds|creates|serves)\b",
    ]

    for pattern in patterns:

        try:

            matches = re.findall(
                pattern,
                text,
            )

        except re.error:
            continue

        for match in matches:

            if isinstance(
                match,
                tuple,
            ):
                match = match[0]

            name = clean_company_candidate(
                str(match)
            )

            if not name:
                continue

            score = company_name_score(
                name
            )

            if score < 60:
                continue

            low = name.lower()

            # Jangan pakai frasa generic.
            generic_phrases = (
                "identify business owners",
                "identify business",
                "find companies",
                "finding the right",
                "the goal",
                "the work",
                "small business",
                "business owners",
                "decision makers",
                "decision-makers",
                "looking for someone",
                "lead generation specialist",
                "virtual assistant",
                "lead researcher",
            )

            if any(
                phrase in low
                for phrase in generic_phrases
            ):
                continue

            if name not in candidates:
                candidates.append(name)

    candidates.sort(
        key=lambda value: (
            company_name_score(value),
            len(value),
        ),
        reverse=True,
    )

    return candidates[:8]


# ============================================================
# INTENT SCORE
# ============================================================

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
        "we are looking",
        "we're looking",
        "now hiring",
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
        "prospect list",
        "targeted prospect",
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

    if any(
        source in query.lower()
        for source in (
            "upwork.com",
            "freelancer.com",
            "guru.com",
            "onlinejobs.ph",
        )
    ):
        score += 5

    return min(
        score,
        100,
    )


# ============================================================
# OFFICIAL WEBSITE RESOLUTION
# ============================================================

def candidate_domain_score(
    candidate_url: str,
    company_name: str,
    title: str,
) -> int:

    if not candidate_url:
        return 0

    candidate_domain = domain(
        candidate_url
    )

    if not candidate_domain:
        return 0

    if is_blocked(
        candidate_url
    ):
        return 0

    low_domain = candidate_domain.lower()
    low_company = company_name.lower()
    low_title = title.lower()

    score = 0

    company_words = [
        word
        for word in re.findall(
            r"[a-z0-9]+",
            low_company,
        )
        if len(word) >= 3
    ]

    for word in company_words:

        if word in low_domain:
            score += 20

    if any(
        token in candidate_url.lower()
        for token in (
            "contact",
            "about",
        )
    ):
        score += 5

    if any(
        bad in low_title
        for bad in (
            "directory",
            "review",
            "ranking",
            "article",
            "blog",
        )
    ):
        score -= 20

    return max(
        0,
        min(
            score,
            100,
        ),
    )


def resolve_company(
    company_name: str,
    job_title: str,
) -> dict:

    result = {
        "company_name": company_name,
        "website": "",
        "email": "",
        "phone": "",
        "website_title": "",
        "website_text": "",
        "source": "",
    }

    if not company_name:
        return result

    queries = [
        f'"{company_name}" official website',
        f'"{company_name}" contact',
        f'"{company_name}" email',
    ]

    candidates: list[dict] = []

    try:

        with DDGS() as ddgs:

            for query in queries:

                try:

                    search_results = ddgs.text(
                        query,
                        max_results=5,
                    )

                except Exception as exc:

                    print(
                        "RESOLUTION QUERY ERROR: "
                        f"{type(exc).__name__}: {exc}"
                    )

                    continue

                for item in (
                    search_results
                    or []
                ):

                    href = normalize(
                        item.get(
                            "href",
                            "",
                        )
                    )

                    title = normalize(
                        item.get(
                            "title",
                            "",
                        )
                    )

                    body = normalize(
                        item.get(
                            "body",
                            "",
                        )
                    )

                    if not href:
                        continue

                    if is_blocked(
                        href
                    ):
                        continue

                    score = candidate_domain_score(
                        href,
                        company_name,
                        title,
                    )

                    if score <= 0:
                        continue

                    candidates.append(
                        {
                            "url": href,
                            "title": title,
                            "body": body,
                            "score": score,
                        }
                    )

    except Exception as exc:

        print(
            "RESOLUTION SEARCH ERROR: "
            f"{type(exc).__name__}: {exc}"
        )

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    checked_domains: set[str] = set()

    for candidate in candidates:

        href = candidate["url"]

        current_domain = domain(
            href
        )

        if current_domain in checked_domains:
            continue

        checked_domains.add(
            current_domain
        )

        try:

            snap = snapshot(
                href
            )

        except Exception:

            continue

        if not snap.get("ok"):
            continue

        final_url = normalize(
            snap.get(
                "final_url",
                href,
            )
        )

        if is_blocked(
            final_url
        ):
            continue

        email = extract_email_from_list(
            snap.get(
                "emails",
                [],
            )
        )

        if not email:

            email = extract_email(
                snap.get(
                    "text",
                    "",
                )
            )

        phone = ""

        for raw_phone in (
            snap.get(
                "phones",
                [],
            )
            or []
        ):

            phone = clean_phone(
                str(
                    raw_phone
                    or ""
                )
            )

            if phone:
                break

        website_text = normalize(
            snap.get(
                "text",
                "",
            )
        )[:6000]

        website_title = normalize(
            snap.get(
                "title",
                "",
            )
        )

        if (
            email
            or phone
            or website_text
        ):

            result.update(
                {
                    "website": final_url,
                    "email": email,
                    "phone": phone,
                    "website_title": website_title,
                    "website_text": website_text,
                    "source": current_domain,
                }
            )

            if email:
                return result

    return result


# ============================================================
# FINGERPRINT
# ============================================================

def fingerprint(
    prospect: dict,
) -> str:

    raw = "|".join(
        str(
            prospect.get(
                field,
                "",
            )
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
        raw.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# DISCOVERY
# ============================================================

def discover(
    limit: int = 30,
) -> list[dict]:

    if limit <= 0:
        return []

    # Rotasi query setiap 30 menit.
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
        f"Query count: "
        f"{len(selected_queries)}"
    )

    print(
        "========================================"
    )

    results_out: list[dict] = []

    seen: set[str] = set()

    company_resolutions = 0

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

            for item in (
                search_results
                or []
            ):

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

                # Hanya ambil job/request.
                if not is_job_domain(
                    href
                ):
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

                if score < 65:
                    continue

                # ====================================================
                # SNAPSHOT JOB
                # ====================================================

                job_email = extract_email(
                    snippet
                )

                job_phone = extract_phone(
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
                        )[:6000]

                        if not job_email:

                            job_email = (
                                extract_email_from_list(
                                    snap.get(
                                        "emails",
                                        [],
                                    )
                                )
                            )

                        if not job_phone:

                            for raw_phone in (
                                snap.get(
                                    "phones",
                                    [],
                                )
                                or []
                            ):

                                candidate_phone = clean_phone(
                                    str(
                                        raw_phone
                                        or ""
                                    )
                                )

                                if candidate_phone:
                                    job_phone = candidate_phone
                                    break

                except Exception as exc:

                    print(
                        "SNAPSHOT WARNING: "
                        f"{href} | "
                        f"{type(exc).__name__}: {exc}"
                    )

                # ====================================================
                # FULL JOB TEXT
                # ====================================================

                full_job_text = normalize(
                    f"{snippet} "
                    f"{website_text}"
                )

                # ====================================================
                # COMPANY CANDIDATE
                # ====================================================

                candidates = extract_company_candidates(
                    full_job_text,
                    title,
                )

                company_name = ""

                if candidates:

                    company_name = candidates[0]

                    print(
                        "COMPANY CANDIDATE: "
                        f"{company_name}"
                    )

                # ====================================================
                # RESOLVE COMPANY
                # ====================================================

                resolved = {
                    "company_name": company_name,
                    "website": "",
                    "email": "",
                    "phone": "",
                    "website_title": "",
                    "website_text": "",
                    "source": "",
                }

                if (
                    company_name
                    and company_resolutions
                    < MAX_COMPANY_RESOLUTION_PER_RUN
                ):

                    company_resolutions += 1

                    print(
                        "RESOLVING COMPANY: "
                        f"{company_name}"
                    )

                    try:

                        resolved = resolve_company(
                            company_name,
                            title,
                        )

                    except Exception as exc:

                        print(
                            "RESOLUTION WARNING: "
                            f"{type(exc).__name__}: {exc}"
                        )

                    resolved_website = (
                        resolved.get(
                            "website",
                            "",
                        )
                    )

                    resolved_email = (
                        resolved.get(
                            "email",
                            "",
                        )
                    )

                    if resolved_website:

                        print(
                            "RESOLVED WEBSITE: "
                            f"{resolved_website}"
                        )

                    if resolved_email:

                        print(
                            "RESOLVED EMAIL: "
                            f"{resolved_email}"
                        )

                # ====================================================
                # FINAL EMAIL
                # ====================================================

                email = (
                    resolved.get(
                        "email",
                        "",
                    )
                    or job_email
                )

                email = clean_email(
                    email
                )

                if is_blocked_email(
                    email
                ):
                    email = ""

                # ====================================================
                # BUSINESS NAME
                # ====================================================

                final_business_name = (
                    resolved.get(
                        "company_name",
                        "",
                    )
                    or company_name
                )

                # Kalau belum ada nama perusahaan,
                # jangan memaksa memakai potongan kalimat.
                if not final_business_name:

                    final_business_name = (
                        "Unknown Buyer"
                    )

                low_business = (
                    final_business_name.lower()
                )

                if any(
                    bad in low_business
                    for bad in (
                        "upwork",
                        "freelancer",
                        "onlinejobs",
                        "guru",
                        "identify business",
                        "decision makers",
                        "decision-makers",
                        "workflow for my agency",
                    )
                ):

                    final_business_name = (
                        "Unknown Buyer"
                    )

                # ====================================================
                # FINAL WEBSITE
                # ====================================================

                resolved_website = normalize(
                    resolved.get(
                        "website",
                        "",
                    )
                )

                # Kalau website resmi tidak ditemukan,
                # kita simpan URL job sebagai source,
                # BUKAN menganggapnya website client.
                final_website = (
                    resolved_website
                    or ""
                )

                # ====================================================
                # FINAL PHONE
                # ====================================================

                final_phone = clean_phone(
                    resolved.get(
                        "phone",
                        "",
                    )
                    or job_phone
                )

                # ====================================================
                # FINAL WEBSITE TEXT
                # ====================================================

                final_website_text = normalize(
                    resolved.get(
                        "website_text",
                        "",
                    )
                    or ""
                )[:6000]

                final_website_title = normalize(
                    resolved.get(
                        "website_title",
                        "",
                    )
                    or ""
                )

                # ====================================================
                # STATUS
                # ====================================================

                outreach_status = (
                    "NEW"
                    if email
                    else "NO_EMAIL"
                )

                # ====================================================
                # PROSPECT
                # ====================================================

                prospect = {
                    "business_name": final_business_name,

                    "niche": (
                        "B2B Lead Generation"
                    ),

                    "city": "",
                    "province": "",

                    "website": final_website,

                    "instagram": "",

                    "email": email,

                    "phone": final_phone,

                    # URL job asli.
                    "source_url": href,

                    "intent_type": (
                        "B2B Lead Generation"
                    ),

                    "intent_source": domain(
                        href
                    ),

                    "intent_url": href,

                    "intent_title": title,

                    "intent_date": "",

                    "intent_budget": "",

                    "intent_score": score,

                    "website_title": (
                        final_website_title
                    ),

                    "website_text": (
                        final_website_text
                    ),

                    "audit_score": "",

                    "audit_summary": "",

                    "outreach_status": (
                        outreach_status
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
                        f"job_title={title} | "
                        f"company_candidate="
                        f"{company_name or 'UNKNOWN'} | "
                        f"resolved_website="
                        f"{resolved_website or 'NO'} | "
                        f"resolved_email="
                        f"{resolved.get('email', '') or 'NO'} | "
                        f"snippet={snippet[:900]}"
                    ),
                }

                # ====================================================
                # DEDUP
                # ====================================================

                fp = fingerprint(
                    prospect
                )

                if fp in seen:
                    continue

                seen.add(fp)

                results_out.append(
                    prospect
                )

                print(
                    "FOUND INTENT: "
                    f"{title} | "
                    f"score={score} | "
                    f"company="
                    f"{final_business_name} | "
                    f"email="
                    f"{email or 'NO EMAIL'}"
                )

                if (
                    len(results_out)
                    >= limit
                ):

                    print(
                        f"\nIntent target reached: "
                        f"{limit}"
                    )

                    return results_out

    # ============================================================
    # FINISHED
    # ============================================================

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
        f"Companies resolved: "
        f"{company_resolutions}"
    )

    print(
        "========================================"
    )

    return results_out
