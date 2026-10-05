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
# JOB DOMAINS
# ============================================================

JOB_DOMAINS = {
    "upwork.com",
    "freelancer.com",
    "guru.com",
    "onlinejobs.ph",
}


# ============================================================
# BLOCKED WEBSITE DOMAINS
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
    "justuseapp.com",
    "wikihow.com",
}


# ============================================================
# BLOCKED EMAIL DOMAINS
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
# BAD PATHS
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
# RESOLUTION LIMIT
# ============================================================

MAX_COMPANY_RESOLUTION_PER_RUN = 12


# ============================================================
# SEARCH BACKENDS
# ============================================================

SEARCH_BACKENDS = (
    "auto",
    "brave",
    "bing",
    "google",
    "duckduckgo",
    "mojeek",
    "startpage",
)


# ============================================================
# BUSINESS SUFFIXES
# ============================================================

BUSINESS_SUFFIXES = (
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


# ============================================================
# BAD COMPANY WORDS
# ============================================================

BAD_COMPANY_EXACT = {
    "we",
    "we are",
    "we're",
    "us",
    "our",
    "i",
    "my",
    "the",
    "company",
    "employer",
    "client",
    "business",
    "agency",
    "team",
    "job",
    "project",
    "project description",
    "project overview",
    "about us",
    "company info",
    "looking for",
    "looking for someone",
    "roofing we",
    "united states we",
}


BAD_COMPANY_WORDS = {
    "we",
    "us",
    "our",
    "i",
    "my",
    "this",
    "that",
    "project",
    "overview",
    "description",
    "requirements",
    "requirement",
    "about",
    "looking",
    "need",
    "needs",
    "seeking",
    "hiring",
    "job",
    "role",
    "position",
    "company",
    "client",
    "employer",
    "team",
}


GENERIC_PHRASES = (
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
    "project description",
    "project overview",
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(
    value: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()


def domain(
    url: str,
) -> str:

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


def normalize_token(
    value: str,
) -> str:

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value or "").lower(),
    )


# ============================================================
# DOMAIN VALIDATION
# ============================================================

def is_job_domain(
    url: str,
) -> bool:

    current = domain(
        url
    )

    return any(
        current == item
        or current.endswith(
            "." + item
        )
        for item in JOB_DOMAINS
    )


def is_blocked(
    url: str,
) -> bool:

    current = domain(
        url
    )

    if not current:
        return True

    return any(
        current == blocked
        or current.endswith(
            "." + blocked
        )
        for blocked in BLOCKED_DOMAINS
    )


# ============================================================
# EMAIL
# ============================================================

def is_blocked_email(
    email: str,
) -> bool:

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


def extract_email(
    text: str,
) -> str:

    if not text:
        return ""

    matches = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text,
    )

    for match in matches:

        email = clean_email(
            match
        )

        if not email:
            continue

        if is_blocked_email(
            email
        ):
            continue

        return email

    return ""


def extract_email_from_list(
    emails,
) -> str:

    if not emails:
        return ""

    for raw_email in emails:

        email = clean_email(
            str(raw_email or "")
        )

        if not email:
            continue

        if is_blocked_email(
            email
        ):
            continue

        return email

    return ""


# ============================================================
# PHONE
# ============================================================

def extract_phone(
    text: str,
) -> str:

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
# DDGS SEARCH
# ============================================================

def search_web(
    ddgs: DDGS,
    query: str,
    max_results: int = 10,
) -> list[dict]:

    collected: list[dict] = []

    seen_urls: set[str] = set()

    for backend in SEARCH_BACKENDS:

        try:

            print(
                f"SEARCH BACKEND: {backend}"
            )

            results = ddgs.text(
                query,
                region="us-en",
                safesearch="moderate",
                max_results=max_results,
                backend=backend,
            )

            if not results:
                continue

            for item in results:

                href = normalize(
                    item.get(
                        "href",
                        "",
                    )
                )

                if not href:
                    continue

                normalized_href = (
                    href.lower()
                    .rstrip("/")
                )

                if normalized_href in seen_urls:
                    continue

                seen_urls.add(
                    normalized_href
                )

                collected.append(
                    item
                )

            if collected:
                break

        except Exception as exc:

            print(
                "SEARCH BACKEND ERROR: "
                f"{backend} | "
                f"{type(exc).__name__}: {exc}"
            )

            time.sleep(
                0.75
            )

    return collected


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
        "i need",
        "we want",
        "we are hiring",
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
        "decision-maker",
        "decision maker",
        "sales development",
        "cold calling",
        "cold caller",
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

    # Listing/category pages are less useful
    # than a specific job.
    if any(
        phrase in title.lower()
        for phrase in (
            "freelance jobs",
            "jobs on upwork",
            "jobs: work remote",
        )
    ):
        score -= 10

    return max(
        0,
        min(
            score,
            100,
        ),
    )


# ============================================================
# COMPANY NAME SCORE
# ============================================================

def company_name_score(
    name: str,
) -> int:

    name = normalize(
        name
    )

    if not name:
        return 0

    low = name.lower().strip()

    if low in BAD_COMPANY_EXACT:
        return 0

    if len(name) > 70:
        return 0

    if any(
        char in name
        for char in (
            ":",
            ";",
            ",",
        )
    ):
        return 0

    # Period hanya untuk suffix bisnis.
    if "." in name:

        allowed = (
            "inc.",
            "ltd.",
            "corp.",
            "co.",
        )

        if not any(
            marker in low
            for marker in allowed
        ):
            return 0

    words = name.split()

    if not 1 <= len(words) <= 7:
        return 0

    normalized_words = {
        normalize_token(word)
        for word in words
    }

    if normalized_words & BAD_COMPANY_WORDS:
        return 0

    if low.startswith(
        (
            "we ",
            "us ",
            "our ",
            "i ",
            "my ",
            "the ",
            "this ",
            "that ",
            "project ",
            "about ",
            "looking ",
            "need ",
            "seeking ",
        )
    ):
        return 0

    score = 50

    if 2 <= len(words) <= 6:
        score += 15

    # Brand satu kata seperti LeadOrbix.
    if len(words) == 1:

        if not re.match(
            r"^[A-Z][A-Za-z0-9&'_-]{3,40}$",
            name,
        ):
            return 0

        score += 20

    for suffix in BUSINESS_SUFFIXES:

        if (
            low.endswith(
                " " + suffix
            )
            or low == suffix
            or low.endswith(
                " " + suffix + "."
            )
        ):

            score += 30

            break

    return max(
        0,
        min(
            score,
            100,
        ),
    )


# ============================================================
# COMPANY CANDIDATE CLEANER
# ============================================================

def clean_company_candidate(
    name: str,
) -> str:

    name = normalize(
        name
    )

    if not name:
        return ""

    name = name.strip(
        " \t\r\n.,:;|-"
    )

    prefixes = (
        "about ",
        "company ",
        "company info ",
        "company information ",
        "employer ",
        "client ",
        "client company ",
        "client name ",
        "business ",
        "business name ",
    )

    low = name.lower()

    for prefix in prefixes:

        if low.startswith(
            prefix
        ):

            name = name[
                len(prefix):
            ].strip()

            break

    return name


# ============================================================
# EXTRACT COMPANY CANDIDATES
# ============================================================

def extract_company_candidates(
    text: str,
    job_title: str,
) -> list[str]:

    if not text:
        return []

    candidates: list[str] = []

    # --------------------------------------------------------
    # Explicit company labels.
    # --------------------------------------------------------

    strong_patterns = [

        r"\bCompany(?:\s+Name| Info| Information)?"
        r"\s*[:\-]\s*"
        r"([A-Z][A-Za-z0-9&'_-]*"
        r"(?:\s+[A-Z][A-Za-z0-9&'_-]*){0,6})",

        r"\bEmployer"
        r"\s*[:\-]\s*"
        r"([A-Z][A-Za-z0-9&'_-]*"
        r"(?:\s+[A-Z][A-Za-z0-9&'_-]*){0,6})",

        r"\bClient(?:\s+Company|\s+Name)?"
        r"\s*[:\-]\s*"
        r"([A-Z][A-Za-z0-9&'_-]*"
        r"(?:\s+[A-Z][A-Za-z0-9&'_-]*){0,6})",

        r"\bBusiness(?:\s+Name)?"
        r"\s*[:\-]\s*"
        r"([A-Z][A-Za-z0-9&'_-]*"
        r"(?:\s+[A-Z][A-Za-z0-9&'_-]*){0,6})",
    ]

    for pattern in strong_patterns:

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

            if (
                company_name_score(
                    name
                )
                < 60
            ):
                continue

            if any(
                phrase in name.lower()
                for phrase in GENERIC_PHRASES
            ):
                continue

            if name not in candidates:

                candidates.append(
                    name
                )

    # --------------------------------------------------------
    # LeadOrbix is a...
    # --------------------------------------------------------

    brand_pattern = (
        r"\b([A-Z][A-Za-z0-9&'_-]{3,40})"
        r"\s+is\s+(?:an?|the)\s+"
    )

    try:

        matches = re.findall(
            brand_pattern,
            text,
        )

    except re.error:

        matches = []

    for match in matches:

        name = clean_company_candidate(
            str(match)
        )

        if not name:
            continue

        if (
            company_name_score(
                name
            )
            < 60
        ):
            continue

        if name not in candidates:

            candidates.append(
                name
            )

    # --------------------------------------------------------
    # About Brand
    # --------------------------------------------------------

    about_pattern = (
        r"\bAbout\s+"
        r"((?!Us\b|We\b|Our\b)"
        r"[A-Z][A-Za-z0-9&'_-]{3,40})"
    )

    try:

        matches = re.findall(
            about_pattern,
            text,
        )

    except re.error:

        matches = []

    for match in matches:

        name = clean_company_candidate(
            str(match)
        )

        if not name:
            continue

        if (
            company_name_score(
                name
            )
            < 60
        ):
            continue

        if name not in candidates:

            candidates.append(
                name
            )

    # --------------------------------------------------------
    # Final rejection.
    # --------------------------------------------------------

    final_candidates = []

    for name in candidates:

        low = name.lower()

        if low in {
            "we",
            "us",
            "our",
            "project",
            "project description",
            "project overview",
            "united states",
            "roofing",
        }:
            continue

        if low.endswith(
            (
                " we",
                " us",
                " our",
            )
        ):
            continue

        if any(
            phrase in low
            for phrase in GENERIC_PHRASES
        ):
            continue

        final_candidates.append(
            name
        )

    final_candidates.sort(
        key=lambda value: (
            company_name_score(
                value
            ),
            len(value),
        ),
        reverse=True,
    )

    return final_candidates[:8]


# ============================================================
# EXPLICIT WEBSITE EXTRACTION
# ============================================================

def extract_explicit_websites(
    text: str,
) -> list[str]:

    if not text:
        return []

    found: list[str] = []

    url_pattern = re.compile(
        r"(?<![@\w])"
        r"(?:(?:https?://|www\.)?"
        r"[a-zA-Z0-9-]+\.[a-zA-Z]{2,}"
        r"(?:/[^\s<>'\"\])}]*)?)"
    )

    for match in url_pattern.findall(
        text
    ):

        raw = normalize(
            match
        ).rstrip(
            ".,;:!?)]}"
        )

        if not raw:
            continue

        url = (
            raw
            if raw.startswith(
                (
                    "http://",
                    "https://",
                )
            )
            else "https://" + raw
        )

        if is_blocked(
            url
        ):
            continue

        if is_job_domain(
            url
        ):
            continue

        current = domain(
            url
        )

        if not current:
            continue

        found.append(
            url
        )

    return list(
        dict.fromkeys(
            found
        )
    )


# ============================================================
# BUSINESS NAME FROM WEBSITE
# ============================================================

def business_name_from_website(
    website_url: str,
    website_title: str,
) -> str:

    title = normalize(
        website_title
    )

    if title:

        parts = re.split(
            r"\s+(?:\||–|—|-)\s+",
            title,
            maxsplit=1,
        )

        first = clean_company_candidate(
            parts[0]
        )

        if (
            first
            and company_name_score(first) >= 40
            and first.lower() not in {
                "home",
                "homepage",
                "welcome",
                "contact",
                "about",
            }
        ):

            return first

    current_domain = domain(
        website_url
    )

    if not current_domain:
        return ""

    labels = current_domain.split(".")

    if len(labels) < 2:
        return ""

    brand = labels[-2]

    if len(brand) < 4:
        return ""

    if brand in {
        "www",
        "mail",
        "app",
        "blog",
        "support",
        "help",
        "docs",
    }:
        return ""

    return brand.capitalize()


# ============================================================
# EXPLICIT WEBSITE RESOLUTION
# ============================================================

def resolve_explicit_website(
    url: str,
    company_name: str = "",
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

    if not url:
        return result

    if is_blocked(
        url
    ):
        return result

    try:

        snap = snapshot(
            url
        )

    except Exception as exc:

        print(
            "EXPLICIT WEBSITE ERROR: "
            f"{type(exc).__name__}: {exc}"
        )

        return result

    if not snap.get(
        "ok"
    ):
        return result

    final_url = normalize(
        snap.get(
            "final_url",
            url,
        )
    )

    if is_blocked(
        final_url
    ):
        return result

    title = normalize(
        snap.get(
            "title",
            "",
        )
    )

    text = normalize(
        snap.get(
            "text",
            "",
        )
    )[:6000]

    email = extract_email_from_list(
        snap.get(
            "emails",
            [],
        )
    )

    if not email:

        email = extract_email(
            text
        )

    phone = ""

    for raw_phone in (
        snap.get(
            "phones",
            [],
        )
        or []
    ):

        candidate = clean_phone(
            str(
                raw_phone or ""
            )
        )

        if candidate:

            phone = candidate

            break

    company = (
        company_name
        or business_name_from_website(
            final_url,
            title,
        )
    )

    if (
        text
        or email
        or phone
    ):

        result.update(
            {
                "company_name": company,
                "website": final_url,
                "email": email,
                "phone": phone,
                "website_title": title,
                "website_text": text,
                "source": domain(
                    final_url
                ),
            }
        )

    return result


# ============================================================
# COMPANY DOMAIN SCORING
# ============================================================

def meaningful_company_tokens(
    company_name: str,
) -> list[str]:

    tokens = re.findall(
        r"[a-z0-9]+",
        company_name.lower(),
    )

    generic = {
        "company",
        "corporation",
        "corp",
        "inc",
        "ltd",
        "llc",
        "group",
        "agency",
        "media",
        "solutions",
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
    }

    return list(
        dict.fromkeys(
            token
            for token in tokens
            if len(token) >= 4
            and token not in generic
        )
    )


def candidate_domain_score(
    candidate_url: str,
    company_name: str,
    title: str,
    body: str = "",
) -> int:

    if not candidate_url:
        return 0

    current_domain = domain(
        candidate_url
    )

    if not current_domain:
        return 0

    if is_blocked(
        candidate_url
    ):
        return 0

    tokens = meaningful_company_tokens(
        company_name
    )

    if not tokens:
        return 0

    low_domain = current_domain.lower()

    matched = sum(
        1
        for token in tokens
        if token in low_domain
    )

    # Domain harus punya hubungan dengan company.
    if matched == 0:
        return 0

    score = 40 + (
        matched * 25
    )

    text = (
        f"{title} {body}"
    ).lower()

    text_matches = sum(
        1
        for token in tokens
        if token in text
    )

    score += min(
        text_matches * 5,
        15,
    )

    return max(
        0,
        min(
            score,
            100,
        ),
    )


# ============================================================
# RESOLVE COMPANY BY SEARCH
# ============================================================

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

                search_results = search_web(
                    ddgs,
                    query,
                    max_results=8,
                )

                for item in search_results:

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
                        body,
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

        if not snap.get(
            "ok"
        ):
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

        final_score = candidate_domain_score(
            final_url,
            company_name,
            normalize(
                snap.get(
                    "title",
                    "",
                )
            ),
            normalize(
                snap.get(
                    "text",
                    "",
                )
            ),
        )

        if final_score <= 0:
            continue

        title = normalize(
            snap.get(
                "title",
                "",
            )
        )

        text = normalize(
            snap.get(
                "text",
                "",
            )
        )[:6000]

        email = extract_email_from_list(
            snap.get(
                "emails",
                [],
            )
        )

        if not email:

            email = extract_email(
                text
            )

        phone = ""

        for raw_phone in (
            snap.get(
                "phones",
                [],
            )
            or []
        ):

            candidate_phone = clean_phone(
                str(
                    raw_phone or ""
                )
            )

            if candidate_phone:

                phone = candidate_phone

                break

        if (
            email
            or phone
            or text
        ):

            result.update(
                {
                    "website": final_url,
                    "email": email,
                    "phone": phone,
                    "website_title": title,
                    "website_text": text,
                    "source": domain(
                        final_url
                    ),
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

    # ========================================================
    # ROTATE QUERY SET EVERY 30 MINUTES
    # ========================================================

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
        for index in range(
            query_count
        )
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

    # ========================================================
    # SEARCH
    # ========================================================

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

            search_results = search_web(
                ddgs,
                query,
                max_results=10,
            )

            if not search_results:

                print(
                    "SEARCH RESULT: "
                    "NO RESULTS FROM AVAILABLE BACKENDS"
                )

                continue

            for item in search_results:

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

                # =================================================
                # ONLY JOB / REQUEST DOMAINS
                # =================================================

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

                # =================================================
                # INTENT SCORE
                # =================================================

                score = intent_score(
                    title,
                    snippet,
                    query,
                )

                if score < 65:
                    continue

                # =================================================
                # JOB SNAPSHOT
                # =================================================

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

                    if snap.get(
                        "ok"
                    ):

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

                                    job_phone = (
                                        candidate_phone
                                    )

                                    break

                except Exception as exc:

                    print(
                        "SNAPSHOT WARNING: "
                        f"{href} | "
                        f"{type(exc).__name__}: {exc}"
                    )

                # =================================================
                # FULL TEXT
                # =================================================

                full_job_text = normalize(
                    f"{snippet} "
                    f"{website_text}"
                )

                # =================================================
                # EXPLICIT WEBSITE
                # =================================================

                explicit_websites = (
                    extract_explicit_websites(
                        full_job_text
                    )
                )

                for explicit_url in (
                    explicit_websites[:5]
                ):

                    print(
                        "EXPLICIT WEBSITE: "
                        f"{explicit_url}"
                    )

                # =================================================
                # COMPANY CANDIDATE
                # =================================================

                candidates = (
                    extract_company_candidates(
                        full_job_text,
                        title,
                    )
                )

                company_name = ""

                if candidates:

                    company_name = (
                        candidates[0]
                    )

                    print(
                        "COMPANY CANDIDATE: "
                        f"{company_name}"
                    )

                else:

                    print(
                        "COMPANY CANDIDATE: UNKNOWN"
                    )

                # =================================================
                # DEFAULT RESOLVED OBJECT
                # =================================================

                resolved = {
                    "company_name": company_name,
                    "website": "",
                    "email": "",
                    "phone": "",
                    "website_title": "",
                    "website_text": "",
                    "source": "",
                }

                # =================================================
                # PRIORITY 1:
                # EXPLICIT WEBSITE FOUND IN JOB
                # =================================================

                if explicit_websites:

                    selected_explicit = ""

                    if company_name:

                        tokens = (
                            meaningful_company_tokens(
                                company_name
                            )
                        )

                        for candidate_url in (
                            explicit_websites
                        ):

                            candidate_domain = (
                                domain(
                                    candidate_url
                                )
                            )

                            if any(
                                token in candidate_domain
                                for token in tokens
                            ):

                                selected_explicit = (
                                    candidate_url
                                )

                                break

                    if not selected_explicit:

                        selected_explicit = (
                            explicit_websites[0]
                        )

                    resolved_explicit = (
                        resolve_explicit_website(
                            selected_explicit,
                            company_name,
                        )
                    )

                    if resolved_explicit.get(
                        "website"
                    ):

                        resolved = (
                            resolved_explicit
                        )

                        if not company_name:

                            company_name = (
                                resolved.get(
                                    "company_name",
                                    "",
                                )
                            )

                            if company_name:

                                print(
                                    "COMPANY CANDIDATE: "
                                    f"{company_name}"
                                )

                # =================================================
                # PRIORITY 2:
                # COMPANY SEARCH
                # =================================================

                if (
                    company_name
                    and not resolved.get(
                        "website"
                    )
                    and company_resolutions
                    < MAX_COMPANY_RESOLUTION_PER_RUN
                ):

                    company_resolutions += 1

                    print(
                        "RESOLVING COMPANY: "
                        f"{company_name}"
                    )

                    try:

                        resolved_from_search = (
                            resolve_company(
                                company_name,
                                title,
                            )
                        )

                        if resolved_from_search.get(
                            "website"
                        ):

                            resolved = (
                                resolved_from_search
                            )

                    except Exception as exc:

                        print(
                            "RESOLUTION WARNING: "
                            f"{type(exc).__name__}: {exc}"
                        )

                elif company_name:

                    print(
                        "RESOLVING COMPANY: "
                        f"{company_name} | "
                        "SKIPPED (run limit reached)"
                    )

                elif not explicit_websites:

                    print(
                        "RESOLVING COMPANY: "
                        "SKIPPED (no reliable company or website)"
                    )

                # =================================================
                # RESOLUTION RESULT
                # =================================================

                resolved_website = normalize(
                    resolved.get(
                        "website",
                        "",
                    )
                )

                resolved_email = clean_email(
                    resolved.get(
                        "email",
                        "",
                    )
                )

                print(
                    "RESOLVED WEBSITE: "
                    f"{resolved_website or 'NO'}"
                )

                print(
                    "RESOLVED EMAIL: "
                    f"{resolved_email or 'NO'}"
                )

                # =================================================
                # FINAL EMAIL
                # =================================================

                email = (
                    resolved_email
                    or job_email
                )

                email = clean_email(
                    email
                )

                if is_blocked_email(
                    email
                ):
                    email = ""

                # =================================================
                # FINAL BUSINESS NAME
                # =================================================

                final_business_name = (
                    resolved.get(
                        "company_name",
                        "",
                    )
                    or company_name
                )

                if not final_business_name:

                    final_business_name = (
                        "Unknown Buyer"
                    )

                # =================================================
                # FINAL WEBSITE
                # =================================================

                final_website = (
                    resolved_website
                    or ""
                )

                # =================================================
                # FINAL PHONE
                # =================================================

                final_phone = clean_phone(
                    resolved.get(
                        "phone",
                        "",
                    )
                    or job_phone
                )

                # =================================================
                # FINAL WEBSITE DATA
                # =================================================

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

                # =================================================
                # STATUS
                # =================================================

                outreach_status = (
                    "NEW"
                    if email
                    else "NO_EMAIL"
                )

                # =================================================
                # NOTES
                # =================================================

                notes = (
                    "INTENT DISCOVERY | "
                    f"query={query} | "
                    f"intent_score={score} | "
                    f"job_title={title} | "
                    f"company_candidate="
                    f"{company_name or 'UNKNOWN'} | "
                    f"explicit_websites="
                    f"{','.join(explicit_websites[:5]) or 'NONE'} | "
                    f"resolved_website="
                    f"{final_website or 'NO'} | "
                    f"resolved_email="
                    f"{resolved_email or 'NO'} | "
                    f"snippet={snippet[:900]}"
                )

                # =================================================
                # PROSPECT
                # =================================================

                prospect = {
                    "business_name":
                        final_business_name,

                    "niche":
                        "B2B Lead Generation",

                    "city":
                        "",

                    "province":
                        "",

                    "website":
                        final_website,

                    "instagram":
                        "",

                    "email":
                        email,

                    "phone":
                        final_phone,

                    "source_url":
                        href,

                    "intent_type":
                        "B2B Lead Generation",

                    "intent_source":
                        domain(
                            href
                        ),

                    "intent_url":
                        href,

                    "intent_title":
                        title,

                    "intent_date":
                        "",

                    "intent_budget":
                        "",

                    "intent_score":
                        score,

                    "website_title":
                        final_website_title,

                    "website_text":
                        final_website_text,

                    "audit_score":
                        "",

                    "audit_summary":
                        "",

                    "outreach_status":
                        outreach_status,

                    "outreach_at":
                        "",

                    "wa_link":
                        "",

                    "message_subject":
                        "",

                    "message_body":
                        "",

                    "email_opt_in":
                        "",

                    "opt_out":
                        "",

                    "notes":
                        notes,
                }

                # =================================================
                # DEDUP
                # =================================================

                fp = fingerprint(
                    prospect
                )

                if fp in seen:
                    continue

                seen.add(
                    fp
                )

                results_out.append(
                    prospect
                )

                print(
                    "FOUND INTENT: "
                    f"{title} | "
                    f"score={score} | "
                    f"company="
                    f"{final_business_name} | "
                    f"website="
                    f"{final_website or 'NO WEBSITE'} | "
                    f"email="
                    f"{email or 'NO EMAIL'}"
                )

                # =================================================
                # LIMIT
                # =================================================

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
