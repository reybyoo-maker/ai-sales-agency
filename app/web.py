from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+62|62|0)(?:[\s().-]*\d){9,14}")


def normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    return value if value.startswith(("http://", "https://")) else "https://" + value


def clean_email(value: str) -> str:
    m = EMAIL_RE.search(value or "")
    if not m:
        return ""
    email = m.group(0).lower().strip().rstrip(".,;:")
    if email in {"you@example.com", "name@example.com", "email@example.com", "test@example.com"}:
        return ""
    return email


def clean_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    return digits if digits.startswith("62") and 10 <= len(digits) <= 15 else ""


def snapshot(url: str) -> dict:
    url = normalize_url(url)
    empty = {"ok": False, "reason": "", "title": "", "text": "", "emails": [], "phones": [], "links": []}
    if not url:
        empty["reason"] = "no website"
        return empty
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0 (compatible; AI-Sales-Scout/1.5)"})
        r.raise_for_status()
        if "text" not in r.headers.get("content-type", "").lower():
            empty["reason"] = "not html"
            return empty
        soup = BeautifulSoup(r.text[:2_000_000], "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:6000]
        emails = sorted({clean_email(x) for x in EMAIL_RE.findall(r.text) if clean_email(x)})[:10]
        phones = sorted({clean_phone(x) for x in PHONE_RE.findall(r.text) if clean_phone(x)})[:10]
        links = []
        for a in soup.find_all("a", href=True)[:120]:
            href = urljoin(r.url, a["href"])
            low = href.lower()
            if any(k in low for k in ("instagram.com/", "wa.me/", "whatsapp.com/", "contact", "kontak", "booking", "reservasi", "order")):
                links.append(href)
        return {"ok": True, "status": r.status_code, "final_url": r.url, "title": title, "text": text, "emails": emails, "phones": phones, "links": sorted(set(links))[:30]}
    except requests.RequestException as exc:
        empty["reason"] = str(exc)[:250]
        return empty
