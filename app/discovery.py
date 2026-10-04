from __future__ import annotations

import hashlib
import re
import time
from urllib.parse import urlparse

from ddgs import DDGS

from .web import clean_email, clean_phone, snapshot

PROVINCES = [
    "Aceh", "Sumatera Utara", "Sumatera Barat", "Riau", "Kepulauan Riau", "Jambi",
    "Sumatera Selatan", "Bengkulu", "Lampung", "Bangka Belitung", "Banten", "DKI Jakarta",
    "Jawa Barat", "Jawa Tengah", "DI Yogyakarta", "Jawa Timur", "Bali", "Nusa Tenggara Barat",
    "Nusa Tenggara Timur", "Kalimantan Barat", "Kalimantan Tengah", "Kalimantan Selatan",
    "Kalimantan Timur", "Kalimantan Utara", "Sulawesi Utara", "Sulawesi Tengah", "Sulawesi Selatan",
    "Sulawesi Tenggara", "Gorontalo", "Sulawesi Barat", "Maluku", "Maluku Utara", "Papua",
    "Papua Barat", "Papua Selatan", "Papua Tengah", "Papua Pegunungan", "Papua Barat Daya",
]

NICHES = [
    "cafe", "coffee shop", "barbershop", "salon", "gym", "fitness", "klinik kecantikan", "spa",
    "laundry", "wedding organizer", "event organizer", "fotografer", "videografer", "studio foto",
    "travel agent", "tour travel", "kursus", "les privat", "bengkel", "car detailing", "MUA",
    "catering", "bakery", "fashion boutique", "toko bunga", "property agent", "jasa interior",
    "kontraktor", "cleaning service", "pet shop", "klinik gigi", "dealer mobil", "sewa mobil",
    "rental mobil",
]

BLOCKED = {
    "tripadvisor.com", "fresha.com", "yelp.com", "wanderlog.com", "bridestory.com", "tempat.info",
    "rekomended.com", "idalamat.com", "indonesiaknowledge.com", "beautynailhairsalons.com",
    "laundry.co.id", "laundryindonesia.com", "barberhead.com", "localoria.com", "yellowpages.co.id",
    "indotrading.com", "wikipedia.org", "kompas.com", "detik.com", "tempo.co", "tokopedia.com",
    "shopee.co.id", "lazada.co.id", "traveloka.com", "gofood.co.id", "grab.com", "facebook.com",
    "youtube.com", "tiktok.com", "linkedin.com", "instagram.com", "linktr.ee",
}
BAD_TITLE = (
    "rekomendasi", "direktori", "directory", "best ", "daftar ", "list ", "near me", "review",
    "reviews", "ranking", "top ", "harga ", "artikel", "news", "berita", "wikipedia",
)


def norm(v: str) -> str:
    return re.sub(r"\s+", " ", v or "").strip()


def dom(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")
    except Exception:
        return ""


def blocked(url: str) -> bool:
    d = dom(url)
    return any(d == x or d.endswith("." + x) for x in BLOCKED)


def likely_business(title: str, href: str, body: str) -> bool:
    if not href.startswith(("http://", "https://")) or blocked(href):
        return False
    t = title.lower()
    b = body.lower()
    if any(x in t for x in BAD_TITLE):
        return False
    if any(x in b for x in ("compare prices", "directory", "list of", "daftar 10", "daftar 20")):
        return False
    return bool(title.strip())


def fingerprint(p: dict) -> str:
    s = "|".join((p.get(k) or "").strip().lower().rstrip("/") for k in ("business_name", "website", "instagram", "email", "phone"))
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def discover(limit: int = 30) -> list[dict]:
    window = int(time.time() // 1800)
    jobs = []
    for province in PROVINCES:
        for niche in NICHES:
            jobs.append((province, niche, f'"{niche}" "{province}" Indonesia official website contact'))
            jobs.append((province, niche, f'"{niche}" "{province}" Indonesia email'))
    start = (window * 8) % len(jobs)
    selected = [jobs[(start + i) % len(jobs)] for i in range(min(8, len(jobs)))]

    out, seen = [], set()
    with DDGS() as ddgs:
        for province, niche, query in selected:
            try:
                results = ddgs.text(query, max_results=10)
            except Exception as exc:
                print(f"DISCOVERY ERROR {query}: {type(exc).__name__}: {exc}")
                continue
            for r in results or []:
                title = norm(r.get("title", ""))
                href = norm(r.get("href", ""))
                snippet = norm(r.get("body", ""))
                if not likely_business(title, href, snippet):
                    continue
                # Only keep prospects that have a real email after a quick site check/snippet check.
                snap = snapshot(href)
                email = (snap.get("emails") or [""])[0] if snap.get("ok") else ""
                phone = (snap.get("phones") or [""])[0] if snap.get("ok") else ""
                instagram = next((x for x in (snap.get("links") or []) if "instagram.com/" in x.lower()), "")
                if not email:
                    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", snippet)
                    if m:
                        email = clean_email(m.group(0))
                if not phone:
                    m = re.search(r"(?:\+62|62|0)(?:[\s().-]*\d){9,14}", snippet)
                    if m:
                        phone = clean_phone(m.group(0))
                if not email:
                    continue
                item = {
                    "business_name": title,
                    "niche": niche,
                    "city": "",
                    "province": province,
                    "website": href,
                    "instagram": instagram,
                    "email": email,
                    "phone": phone,
                    "source_url": href,
                    "audit_score": "",
                    "audit_summary": "",
                    "outreach_status": "NEW",
                    "outreach_at": "",
                    "wa_link": "",
                    "message_subject": "",
                    "message_body": "",
                    "notes": f"Source query: {query}; snippet: {snippet[:500]}",
                    "opt_out": "",
                }
                fp = fingerprint(item)
                if fp in seen:
                    continue
                seen.add(fp)
                out.append(item)
                if len(out) >= limit:
                    return out
    return out
