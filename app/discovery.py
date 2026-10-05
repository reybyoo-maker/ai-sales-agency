from __future__ import annotations

import hashlib
import re
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
    SEARCH_RESULTS_PER_QUERY,
)

MONTHS = {
    "jan": 1, "januari": 1, "january": 1, "feb": 2, "februari": 2, "february": 2,
    "mar": 3, "maret": 3, "march": 3, "apr": 4, "april": 4, "mei": 5, "may": 5,
    "jun": 6, "juni": 6, "june": 7, "jul": 7, "juli": 7, "july": 7,
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
    hay = f"{title} {text}".lower()
    if any(term in hay for term in MARKETING_TERMS):
        return "marketing"
    if any(term in hay for term in BACK_OFFICE_TERMS):
        return "back_office"
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

def search_once() -> list[dict]:
    now = datetime.now().astimezone()
    queries = [
        f'"{LOCATION_QUERY}" lowongan marketing gmail',
        f'"{LOCATION_QUERY}" lowongan "digital marketing" gmail',
        f'"{LOCATION_QUERY}" lowongan "social media" gmail',
        f'"{LOCATION_QUERY}" lowongan "content creator" gmail',
        f'"{LOCATION_QUERY}" lowongan brand gmail',
        f'"{LOCATION_QUERY}" lowongan "marketing communication" gmail',
        f'"{LOCATION_QUERY}" lowongan admin gmail',
        f'"{LOCATION_QUERY}" lowongan accounting gmail',
        f'"{LOCATION_QUERY}" lowongan finance gmail',
        f'"{LOCATION_QUERY}" lowongan HRD gmail',
        f'"{LOCATION_QUERY}" lowongan recruitment gmail',
        f'"{LOCATION_QUERY}" lowongan purchasing gmail',
        f'"{LOCATION_QUERY}" lowongan procurement gmail',
        f'"{LOCATION_QUERY}" lowongan legal gmail',
        f'"{LOCATION_QUERY}" lowongan secretary gmail',
        f'"{LOCATION_QUERY}" lowongan operations gmail',
        f'"{LOCATION_QUERY}" lowongan "back office" gmail',
        f'"{LOCATION_QUERY}" lowongan "staff administrasi" gmail',
        f'"{LOCATION_QUERY}" lowongan "customer service" gmail',
        f'"{LOCATION_QUERY}" lowongan remote gmail',
        f'"{LOCATION_QUERY}" lowongan hybrid gmail',
        f'site:glints.com "{LOCATION_QUERY}" lowongan gmail',
        f'site:id.indeed.com "{LOCATION_QUERY}" lowongan gmail',
        f'site:jobstreet.co.id "{LOCATION_QUERY}" lowongan gmail',
        f'site:kalibrr.com "{LOCATION_QUERY}" gmail',
        f'site:karir.com "{LOCATION_QUERY}" gmail',
    ]

    rows: list[dict] = []
    seen: set[str] = set()

    with DDGS() as ddgs:
        for query in queries:
            try:
                items = ddgs.text(query, region="id-id", safesearch="moderate", max_results=SEARCH_RESULTS_PER_QUERY, backend="auto")
            except Exception as exc:
                print(f"SEARCH ERROR | {type(exc).__name__}: {exc}")
                continue

            for item in items or []:
                url = normalize(item.get("href", ""))
                title = normalize(item.get("title", ""))
                snippet = normalize(item.get("body", ""))
                if not url or not title:
                    continue

                search_text = normalize(f"{title} {snippet}")
                page_text = ""
                email = extract_gmail(search_text)
                if not email:
                    page_text = fetch_page(url)
                    email = extract_gmail(page_text)
                if not email:
                    continue

                full_text = normalize(f"{search_text} {page_text}")
                if LOCATION_QUERY.lower() not in full_text.lower():
                    continue
                if not has_application_context(full_text, email):
                    continue

                category = classify(title, full_text)
                if not category:
                    continue

                fresh, published, date_status = freshness(full_text, str(item.get("date", "")), now)
                if not fresh:
                    continue

                job_id = make_id(title, email, url)
                if job_id in seen:
                    continue
                seen.add(job_id)

                rows.append({
                    "job_id": job_id,
                    "job_title": title[:180],
                    "company": extract_company(title, full_text) or "Perusahaan",
                    "category": category,
                    "work_mode": work_mode(full_text),
                    "location": LOCATION_QUERY,
                    "source_url": url,
                    "source_domain": domain(url),
                    "published_date": published,
                    "deadline_date": "",
                    "date_status": date_status,
                    "recipient_email": email,
                    "snippet": search_text[:1500],
                    "notes": f"query={query}",
                })

                if len(rows) >= MAX_DISCOVERED_PER_RUN:
                    return rows

    return rows
