from __future__ import annotations
import csv
import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List

from ddgs import DDGS

CITIES = [
    'Jakarta', 'Bandung', 'Bekasi', 'Depok', 'Bogor', 'Tangerang', 'Semarang',
    'Surabaya', 'Malang', 'Yogyakarta', 'Solo', 'Medan', 'Palembang', 'Pekanbaru',
    'Batam', 'Padang', 'Bandar Lampung', 'Pontianak', 'Banjarmasin', 'Balikpapan',
    'Samarinda', 'Makassar', 'Manado', 'Denpasar', 'Mataram', 'Kupang', 'Jayapura'
]
NICHES = [
    'cafe', 'barbershop', 'salon', 'gym', 'fitness', 'klinik kecantikan', 'spa',
    'laundry', 'wedding organizer', 'fotografer', 'travel', 'property agent',
    'dealer mobil', 'bengkel', 'kursus', 'les privat', 'bakery', 'catering',
    'event organizer', 'kontraktor', 'interior', 'fashion', 'jasa service'
]

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+62|62|0)[\s.-]?(?:8\d{2})[\d\s.-]{5,12}")


def norm(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or '').strip())


def extract_email(text: str) -> str:
    m = EMAIL_RE.search(text or '')
    return m.group(0) if m else ''


def extract_phone(text: str) -> str:
    m = PHONE_RE.search(text or '')
    return re.sub(r'[^0-9+]', '', m.group(0)) if m else ''


def fingerprint(item: Dict[str, str]) -> str:
    base = (item.get('website') or item.get('instagram') or item.get('email') or item.get('business_name')).lower()
    return hashlib.sha1(base.encode()).hexdigest()


def discover(limit: int = 25) -> List[Dict[str, str]]:
    # Rotate through a small, diverse set of city+niche searches.
    jobs = []
    for city in CITIES[:10]:
        for niche in NICHES[:6]:
            jobs.append(f'"{niche}" "{city}" Indonesia')
    jobs = jobs[: max(limit, 10)]

    out, seen = [], set()
    with DDGS() as ddgs:
        for q in jobs:
            try:
                results = ddgs.text(q, max_results=5)
            except Exception:
                continue
            for r in results or []:
                title = norm(r.get('title',''))
                href = norm(r.get('href',''))
                snippet = norm(r.get('body',''))
                blob = f'{title} {snippet}'
                item = {
                    'business_name': title,
                    'niche': '',
                    'city': '',
                    'province': '',
                    'website': href if href.startswith('http') else '',
                    'instagram': href if 'instagram.com/' in href else '',
                    'email': extract_email(blob),
                    'phone': extract_phone(blob),
                    'source_url': href,
                    'audit_score': '',
                    'audit_summary': '',
                    'outreach_status': 'NEW',
                    'outreach_at': '',
                    'wa_link': '',
                    'message_subject': '',
                    'message_body': '',
                    'notes': f'Source query: {q}; snippet: {snippet[:500]}',
                    'opt_out': '',
                }
                # Basic location/niche tags from the query rather than invented data.
                parts = q.replace('"','').split()
                if len(parts) >= 2:
                    item['niche'] = ' '.join(parts[:-2]) if len(parts) > 2 else parts[0]
                    item['city'] = parts[-2]
                fp = fingerprint(item)
                if fp in seen or not title or not href:
                    continue
                seen.add(fp)
                out.append(item)
                if len(out) >= limit:
                    return out
    return out


def append_to_csv(rows: List[Dict[str, str]], path='data/prospects.csv'):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fields = ['business_name','niche','city','province','website','instagram','email','phone','source_url','audit_score','audit_summary','outreach_status','outreach_at','wa_link','message_subject','message_body','notes','opt_out']
    exists = Path(path).exists()
    with open(path, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerows(rows)
