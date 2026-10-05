from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

from .config import (
    ALLOW_UNKNOWN_DATE,
    APPLICATION_TERMS,
    BACK_OFFICE_TERMS,
    LOCATION_QUERY,
    MARKETING_TERMS,
    MAX_AGE_DAYS,
    MAX_DISCOVERED_PER_RUN,
    OPEN_BLOCK_TERMS,
    SEARCH_BACKENDS,
    SEARCH_DELAY_SECONDS,
    SEARCH_RETRY_DELAY_SECONDS,
    SEARCH_RESULTS_PER_QUERY,
)

MONTHS = {
    "jan": 1, "januari": 1, "january": 1, "feb": 2, "februari": 2, "february": 2,
    "mar": 3, "maret": 3, "march": 3, "apr": 4, "april": 4, "mei": 5, "may": 5,
    "jun": 6, "juni": 6, "june": 6, "jul": 7, "juli": 7, "july": 7,
    "agu": 8, "agustus": 8, "aug": 8, "sep": 9, "september": 9,
    "okt": 10, "oktober": 10, "oct": 10, "october": 10, "nov": 11, "november": 11,
    "des": 12, "desember": 12, "dec": 12, "december": 12,
}

DATE_RE = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,10})\s+(20\d{2})\b|\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", re.I)
RELATIVE_RE = re.compile(r"\b(\d+)\s*(day|days|hari|week|weeks|minggu|month|months|bulan)\s*(ago|lalu)?\b|\b(today|hari ini|yesterday|kemarin)\b", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+\s*(?:@|\[at\]|\(at\)|#)\s*[A-Za-z0-9.-]+\s*(?:\.|\[dot\]|\(dot\))\s*gmail\.com", re.I)

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()

def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")
    except Exception:
        return ""

def make_id(title: str, email: str, url: str) -> str:
    raw = f"{normalize(title).lower()}|{email.lower()}|{url.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

def parse_date(value: str, now: datetime) -> datetime | None:
    value = normalize(value).lower()
    for m in DATE_RE.finditer(value):
        try:
            g = m.groups()
            if g[0] and g[1] and g[2]:
                month = MONTHS.get(g[1].strip("."))
                if month:
                    return datetime(int(g[2]), month, int(g[0]), tzinfo=now.tzinfo)
            if g[3] and g[4] and g[5]:
                return datetime(int(g[3]), int(g[4]), int(g[5]), tzinfo=now.tzinfo)
        except ValueError:
            pass
    m = RELATIVE_RE.search(value)
    if not m:
        return None
    whole = m.group(0).lower()
    if whole in {"today", "hari ini"}:
        return now
    if whole in {"yesterday", "kemarin"}:
        return now - timedelta(days=1)
    n = int(m.group(1))
    unit = m.group(2).lower()
    if unit.startswith(("day", "hari")):
        return now - timedelta(days=n)
    if unit.startswith(("week", "minggu")):
        return now - timedelta(days=n * 7)
    return now - timedelta(days=n * 30)

def normalize_email(raw: str) -> str:
    value = re.sub(r"\s+", "", str(raw or "").strip().lower())
    return value.replace("[at]", "@").replace("(at)", "@").replace("#", "@").replace("[dot]", ".").replace("(dot)", ".")

def extract_gmail(text: str) -> str:
    for match in EMAIL_RE.finditer(text or ""):
        email = normalize_email(match.group(0))
        if email.endswith("@gmail.com") and not email.startswith(("noreply@", "no-reply@")):
            return email
    return ""

def classify(title: str, text: str) -> str:
    title_hay = normalize(title).lower()
    # The title is the strongest signal. This avoids classifying an admin/legal/
    # customer-service role as marketing just because the source page mentions
    # marketing elsewhere.
    if any(term in title_hay for term in MARKETING_TERMS):
        return "marketing"
    if any(term in title_hay for term in BACK_OFFICE_TERMS):
        return "back_office"

    context = normalize(text).lower()[:5000]
    marketing_hits = sum(1 for term in MARKETING_TERMS if term in context)
    back_office_hits = sum(1 for term in BACK_OFFICE_TERMS if term in context)
    if back_office_hits > marketing_hits and back_office_hits > 0:
        return "back_office"
    if marketing_hits > 0:
        return "marketing"
    return ""

def work_mode(text: str) -> str:
    hay = text.lower()
    for mode in ("remote", "hybrid", "freelance", "contract", "kontrak", "part-time", "part time", "full-time", "full time", "internship", "magang"):
        if mode in hay:
            return mode
    return "unspecified"

def has_application_context(text: str, email: str) -> bool:
    low = text.lower()
    pos = low.find(email.lower())
    segment = low[max(0, pos - 250):pos + 250] if pos >= 0 else low
    return any(term in segment for term in APPLICATION_TERMS)


FAMOUS_COMPANIES = (
    "astra", "unilever", "loreal", "l'oreal", "danone", "eiger", "telkom",
    "bca", "bank mandiri", "bri", "bni", "grab", "gojek", "tokopedia",
    "shopee", "traveloka", "dale carnegie",
)

def company_tier(name: str, text: str) -> str:
    hay = f"{normalize(name)} {normalize(text)}".lower()
    return "famous" if any(company in hay for company in FAMOUS_COMPANIES) else "standard"

def extract_company(title: str, text: str) -> str:
    patterns = [
        r"(?:\bat\b|\bdi\b|\bperusahaan\b|\bcompany\b|\bemployer\b)\s*[:\-]?\s*([A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*){0,6})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            value = normalize(m.group(1)).strip(" .,-:")
            if 2 <= len(value) <= 100:
                return value
    m = re.search(r"\b(?:at|di)\s+(.+)$", title, re.I)
    return normalize(m.group(1))[:100] if m else ""

def fetch_page(url: str) -> str:
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (compatible; BandungJobHunter/3.0)"})
        r.raise_for_status()
        if "text" not in r.headers.get("content-type", "").lower():
            return ""
        soup = BeautifulSoup(r.text[:3_000_000], "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        return normalize(soup.get_text(" ", strip=True))[:14000]
    except requests.RequestException:
        return ""

def freshness(text: str, search_date: str, now: datetime) -> tuple[bool, str, str]:
    low = text.lower()
    if any(term in low for term in OPEN_BLOCK_TERMS):
        return False, "", "closed"

    published = ""
    for label in ("posted", "published", "diposting", "dipublikasikan", "terbit", "dibuat", "updated", "diperbarui"):
        pos = low.find(label)
        if pos >= 0:
            dt = parse_date(text[pos:pos + 240], now)
            if dt:
                published = dt.date().isoformat()
                break

    published_dt = parse_date(published, now) if published else None
    if not published_dt and search_date:
        published_dt = parse_date(search_date, now)

    deadline = ""
    for label in ("deadline", "batas lamaran", "apply by", "berlaku sampai", "closing date"):
        pos = low.find(label)
        if pos >= 0:
            dt = parse_date(text[pos:pos + 240], now)
            if dt:
                deadline = dt.date().isoformat()
                if dt.date() < now.date():
                    return False, published, "deadline_passed"
                break

    if published_dt:
        age = (now.date() - published_dt.date()).days
        return (age <= MAX_AGE_DAYS, published, "fresh" if age <= MAX_AGE_DAYS else "too_old")

    if deadline:
        return True, published, "deadline_open"

    if ALLOW_UNKNOWN_DATE:
        return True, published, "unknown_date_allowed"

    return False, published, "date_unknown"

def prospect_score(title: str, text: str, category: str, company_tier_value: str, recipient_email: str, published: str, date_status: str, source_domain: str) -> tuple[int, str]:
    hay = f"{title} {text}".lower()
    score = 0
    reasons = []

    if date_status == "fresh":
        dt = parse_date(published, datetime.now().astimezone()) if published else None
        if dt:
            age = max(0, (datetime.now().astimezone().date() - dt.date()).days)
            freshness_points = max(10, 40 - min(age, 14) * 2)
        else:
            freshness_points = 25
        score += freshness_points
        reasons.append(f"freshness +{freshness_points}")
    elif date_status == "deadline_open":
        score += 35
        reasons.append("deadline aktif +35")

    if recipient_email:
        score += 25
        reasons.append("Gmail lamaran +25")

    if category == "marketing":
        score += 20
        reasons.append("marketing +20")
    elif category == "back_office":
        score += 18
        reasons.append("back office +18")

    if company_tier_value == "famous":
        score += 10
        reasons.append("perusahaan terkenal +10")

    if source_domain in {"linkedin.com", "jobstreet.co.id", "glints.com", "indeed.com", "kalibrr.com"}:
        score += 5
        reasons.append("sumber job market +5")

    return min(score, 100), "; ".join(reasons)

def search_once() -> list[dict]:
    now = datetime.now().astimezone()
    # Keep the query set compact enough to avoid search-provider throttling.
    # Search broadly first, then classify after fetching each result.
    queries = [
        f'"{LOCATION_QUERY}" lowongan marketing',
        f'"{LOCATION_QUERY}" lowongan digital marketing',
        f'"{LOCATION_QUERY}" lowongan social media',
        f'"{LOCATION_QUERY}" lowongan content creator',
        f'"{LOCATION_QUERY}" lowongan admin',
        f'"{LOCATION_QUERY}" lowongan accounting finance',
        f'"{LOCATION_QUERY}" lowongan HRD recruitment',
        f'"{LOCATION_QUERY}" lowongan purchasing procurement',
        f'"{LOCATION_QUERY}" lowongan legal secretary',
        f'"{LOCATION_QUERY}" lowongan operations',
        f'"{LOCATION_QUERY}" lowongan customer service',
        f'"{LOCATION_QUERY}" lowongan back office',
        f'"{LOCATION_QUERY}" lowongan sales marketing',
        f'site:glints.com "{LOCATION_QUERY}" lowongan',
        f'site:id.indeed.com "{LOCATION_QUERY}" lowongan',
        f'site:jobstreet.co.id "{LOCATION_QUERY}" lowongan',
        f'site:kalibrr.com "{LOCATION_QUERY}" lowongan',
        f'site:karir.com "{LOCATION_QUERY}" lowongan',
        f'"{LOCATION_QUERY}" lowongan Astra',
        f'"{LOCATION_QUERY}" lowongan Unilever',
        f'"{LOCATION_QUERY}" lowongan Danone',
        f'"{LOCATION_QUERY}" lowongan EIGER',
        f'"{LOCATION_QUERY}" lowongan Telkom',
        f'"{LOCATION_QUERY}" lowongan BCA',
        f'"{LOCATION_QUERY}" lowongan BRI',
        f'"{LOCATION_QUERY}" lowongan BNI',
        f'"{LOCATION_QUERY}" lowongan Grab',
        f'"{LOCATION_QUERY}" lowongan Gojek',
        f'"{LOCATION_QUERY}" lowongan Tokopedia',
        f'"{LOCATION_QUERY}" lowongan Shopee',
        f'"{LOCATION_QUERY}" lowongan Traveloka',
    ]

    rows: list[dict] = []
    seen: set[str] = set()

    with DDGS(timeout=15) as ddgs:
        for query_index, query in enumerate(queries, start=1):
            items = []
            for backend_name in SEARCH_BACKENDS:
                try:
                    items = ddgs.text(
                        query,
                        region="id-id",
                        safesearch="moderate",
                        max_results=SEARCH_RESULTS_PER_QUERY,
                        backend=backend_name,
                    )
                    if items:
                        print(
                            f"SEARCH OK | query={query_index}/{len(queries)} "
                            f"backend={backend_name} results={len(items)}"
                        )
                        break
                except Exception as exc:
                    print(
                        f"SEARCH ERROR | query={query_index}/{len(queries)} "
                        f"backend={backend_name} | {type(exc).__name__}: {exc}"
                    )
                    time.sleep(SEARCH_RETRY_DELAY_SECONDS)

            if not items:
                print(f"SEARCH SKIPPED | query={query_index}/{len(queries)}")
            time.sleep(SEARCH_DELAY_SECONDS)

            for item in items or []:
                url = normalize(item.get("href", ""))
                title = normalize(item.get("title", ""))
                snippet = normalize(item.get("body", ""))
                if not url or not title:
                    continue

                search_text = normalize(f"{title} {snippet}")
                title_and_snippet = search_text.lower()
                vacancy_signals = (
                    "lowongan", "lowong", "loker", "job vacancy", "vacancy",
                    "career", "careers", "recruitment", "hiring", "apply",
                    "staff", "specialist", "executive", "officer", "advisor",
                    "assistant", "manager", "supervisor", "coordinator",
                    "admin", "accounting", "finance", "hr", "hrd", "legal",
                    "secretary", "operations", "customer service", "marketing",
                    "content", "social media", "sales", "procurement",
                    "purchasing", "warehouse", "logistics", "brand", "seo", "kol",
                    "partnership", "business development",
                )
                if not any(signal in title_and_snippet for signal in vacancy_signals):
                    continue

                page_text = fetch_page(url)
                full_text = normalize(f"{search_text} {page_text}")
                if LOCATION_QUERY.lower() not in full_text.lower():
                    continue

                email = extract_gmail(search_text)
                if not email:
                    email = extract_gmail(page_text)

                extracted_company = extract_company(title, full_text)
                famous_without_gmail = (
                    company_tier(extracted_company, title) == "famous" and not email
                )
                if not email and not famous_without_gmail:
                    continue
                if email and not has_application_context(full_text, email):
                    continue

                category = classify(title, full_text)
                if not category:
                    continue

                fresh, published, date_status = freshness(
                    full_text, str(item.get("date", "")), now
                )
                if not fresh:
                    continue

                tier = company_tier(extracted_company, title)
                published_dt = parse_date(published, now) if published else None
                age_days = max(0, (now.date() - published_dt.date()).days) if published_dt else ""
                score, score_reason = prospect_score(
                    title, full_text, category, tier, email, published, date_status, domain(url)
                )
                job_id = make_id(title, email, url)
                if job_id in seen:
                    continue
                seen.add(job_id)

                rows.append({
                    "job_id": job_id,
                    "job_title": title[:180],
                    "company": extracted_company or "Perusahaan",
                    "company_tier": tier,
                    "category": category,
                    "work_mode": work_mode(full_text),
                    "location": LOCATION_QUERY,
                    "source_url": url,
                    "source_domain": domain(url),
                    "published_date": published,
                    "deadline_date": "",
                    "date_status": date_status,
                    "age_days": age_days if published else "",
                    "recipient_email": email,
                    "application_method": "GMAIL" if email else "PORTAL/ATS",
                    "prospect_score": score,
                    "score_reason": score_reason,
                    "snippet": search_text[:1500],
                    "notes": f"query={query}",
                })

                if len(rows) >= MAX_DISCOVERED_PER_RUN:
                    return rows

    return rows
