from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

# Major Indonesian cities used as rotating search anchors. The agent also runs
# nationwide queries so it is not restricted to one city.
CITIES = [
    'Jakarta', 'Surabaya', 'Bandung', 'Medan', 'Semarang', 'Makassar', 'Palembang',
    'Tangerang', 'Depok', 'Bekasi', 'Bogor', 'Yogyakarta', 'Malang', 'Denpasar',
    'Batam', 'Pekanbaru', 'Bandar Lampung', 'Padang', 'Samarinda', 'Banjarmasin',
    'Balikpapan', 'Pontianak', 'Manado', 'Mataram', 'Solo', 'Cirebon', 'Tasikmalaya',
    'Serang', 'Kediri', 'Jambi', 'Banda Aceh', 'Bengkulu', 'Palangkaraya',
    'Kupang', 'Jayapura', 'Ambon', 'Ternate', 'Palu', 'Kendari', 'Gorontalo',
    'Sukabumi', 'Purwokerto', 'Cimahi', 'Jember', 'Batu', 'Probolinggo', 'Madiun',
    'Salatiga', 'Magelang', 'Kudus', 'Pontianak'
]

NICHES = [
    'cafe', 'coffee shop', 'barbershop', 'salon', 'gym', 'fitness', 'klinik kecantikan',
    'spa', 'laundry', 'wedding organizer', 'event organizer', 'fotografer',
    'videografer', 'studio foto', 'travel agent', 'tour travel', 'kursus',
    'les privat', 'bengkel', 'car detailing', 'make up artist', 'MUA', 'catering',
    'bakery', 'fashion boutique', 'toko bunga', 'property agent', 'notaris',
    'jasa interior', 'kontraktor', 'cleaning service', 'pet shop', 'klinik gigi',
    'dealer mobil', 'sewa mobil', 'rental mobil'
]

# Domains that are usually directories, review sites, aggregators, marketplaces,
# social search pages, or generic content sites rather than the actual business.
BLOCKED_DOMAINS = {
    'tripadvisor.com', 'fresha.com', 'yelp.com', 'tiktok.com', 'facebook.com',
    'youtube.com', 'linkedin.com', 'tokopedia.com', 'shopee.co.id', 'lazada.co.id',
    'traveloka.com', 'gofood.co.id', 'grab.com', 'kompas.com', 'detik.com',
    'instagram.com', 'localoria.com', 'tempat.info', 'direktoriindonesia.id',
    'yellowpages.co.id', 'indotrading.com', 'olx.co.id', 'idntimes.com',
}

BLOCKED_TITLE = {
    'rekomendasi', 'direktori', 'directory', 'daftar ', 'list ', 'near me',
    'tempat terbaik', 'salon terbaik', 'cafe terbaik', 'best hair salons',
    'menu, prices & restaurant reviews', 'restaurant reviews', 'ulasan',
    'review', 'ranking', 'top ', 'harga ', '7 rekomendasi', '10 rekomendasi',
}

EMAIL_RE = re.compile(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', re.I)
PHONE_RE = re.compile(r'(?:\+62|62|0)(?:\s|[-.]?)(?:\d[\s.-]?){8,13}\d')

CONTACT_PATHS = ('contact', 'kontak', 'hubungi', 'about', 'tentang', 'booking')


def norm(value: str) -> str:
    return re.sub(r'\s+', ' ', (value or '')).strip()


def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().split(':')[0].removeprefix('www.')
    except Exception:
        return ''


def looks_like_directory(title: str, url: str) -> bool:
    d = domain(url)
    t = title.lower()
    if any(d == blocked or d.endswith('.' + blocked) for blocked in BLOCKED_DOMAINS):
        return True
    return any(word in t for word in BLOCKED_TITLE)


def likely_business_page(title: str, url: str, snippet: str) -> bool:
    """Reject generic article/list pages while allowing real business homepages."""
    if looks_like_directory(title, url):
        return False
    if not url.startswith(('http://', 'https://')):
        return False

    t = title.lower()
    s = snippet.lower()
    bad_patterns = (
        'site: ', 'search results', 'all results', 'wikipedia', 'press release',
        'artikel', 'blog', 'news', 'cara ', 'tips ', 'contoh ', 'rekomendasi',
        'lowongan', 'job vacancy', 'lowongan kerja', 'harga tiket',
    )
    if any(p in t for p in bad_patterns):
        return False

    # Strong business signals in title/snippet improve precision.
    business_signals = (
        'official', 'official website', 'booking', 'reservasi', 'reservation',
        'menu', 'services', 'layanan', 'contact', 'kontak', 'whatsapp',
        'alamat', 'lokasi', 'open ', 'studio', 'clinic', 'klinik', 'salon',
        'barbershop', 'cafe', 'coffee', 'gym', 'fitness', 'laundry', 'travel',
    )
    return any(p in t or p in s for p in business_signals) or bool(title.strip())


def _clean_phone(value: str) -> str:
    raw = re.sub(r'[^0-9+]', '', value or '')
    if raw.startswith('+62'):
        return '62' + raw[3:]
    if raw.startswith('0'):
        return '62' + raw[1:]
    if raw.startswith('62'):
        return raw
    return raw


def extract_contacts(html: str) -> tuple[str, str, str, str]:
    emails = EMAIL_RE.findall(html or '')
    phones = PHONE_RE.findall(html or '')
    instagram = ''
    whatsapp = ''
    try:
        soup = BeautifulSoup(html or '', 'html.parser')
        for a in soup.find_all('a', href=True):
            href = norm(a.get('href', ''))
            low = href.lower()
            if not instagram and 'instagram.com/' in low:
                instagram = href
            if not whatsapp and ('wa.me/' in low or 'api.whatsapp.com/' in low or 'whatsapp.com/send' in low):
                whatsapp = href
    except Exception:
        pass
    email = emails[0].strip() if emails else ''
    phone = _clean_phone(phones[0]) if phones else ''
    return email, phone, instagram, whatsapp


def extract_contacts_from_text(text: str) -> tuple[str, str, str]:
    emails = EMAIL_RE.findall(text or '')
    phones = PHONE_RE.findall(text or '')
    instagram = ''
    m = re.search(r'https?://(?:www\.)?instagram\.com/[A-Za-z0-9_.-]+', text or '', re.I)
    if m:
        instagram = m.group(0)
    email = emails[0].strip() if emails else ''
    phone = _clean_phone(phones[0]) if phones else ''
    return email, phone, instagram


def _fetch(url: str) -> str:
    try:
        r = requests.get(
            url,
            timeout=8,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; AI-Sales-Agency/1.2)'},
            allow_redirects=True,
        )
        if 200 <= r.status_code < 400 and 'text' in r.headers.get('content-type', '').lower():
            return r.text[:2_000_000]
    except requests.RequestException:
        pass
    return ''


def enrich(url: str) -> tuple[str, str, str]:
    if not url.startswith(('http://', 'https://')) or looks_like_directory('', url):
        return '', '', ''

    html = _fetch(url)
    if not html:
        return '', '', ''

    email, phone, instagram, whatsapp = extract_contacts(html)

    # If homepage has no direct email/phone, inspect a likely contact page.
    if not email and not phone:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            candidates = []
            base = urlparse(url)
            for a in soup.find_all('a', href=True):
                label = norm(a.get_text(' ', strip=True)).lower()
                href = a.get('href', '')
                low = href.lower()
                if any(path in label or path in low for path in CONTACT_PATHS):
                    if href.startswith('http'):
                        candidates.append(href)
                    elif href.startswith('/'):
                        candidates.append(f'{base.scheme}://{base.netloc}{href}')
            for contact_url in candidates[:2]:
                chtml = _fetch(contact_url)
                if not chtml:
                    continue
                ce, cp, ci, cw = extract_contacts(chtml)
                email = email or ce
                phone = phone or cp
                instagram = instagram or ci
                whatsapp = whatsapp or cw
                if email or phone:
                    break
        except Exception:
            pass

    return email, phone, instagram or whatsapp


def fingerprint(item: Dict[str, str]) -> str:
    base = (
        item.get('website') or item.get('instagram') or item.get('email') or
        item.get('phone') or item.get('business_name')
    ).lower()
    return hashlib.sha1(base.encode('utf-8')).hexdigest()


def _rotating_jobs() -> list[tuple[str, str, str]]:
    jobs: list[tuple[str, str, str]] = []

    # High-intent query patterns tend to surface actual business pages better
    # than a plain '<niche> <city>' search.
    query_templates = [
        '"{niche}" "{city}" Indonesia official website',
        '"{niche}" "{city}" Indonesia WhatsApp',
        '"{niche}" "{city}" Indonesia contact',
        '"{niche}" "{city}" Instagram website',
    ]

    for city in CITIES:
        for niche in NICHES:
            for template in query_templates[:2]:
                jobs.append((niche, city, template.format(niche=niche, city=city)))

    # Add nationwide terms to reach businesses outside the city anchors.
    for niche in NICHES:
        jobs.append((niche, 'Indonesia', f'"{niche}" Indonesia official website WhatsApp'))

    return jobs


def discover(limit: int = 50) -> List[Dict[str, str]]:
    jobs = _rotating_jobs()
    if not jobs:
        return []

    # A GitHub run should not hammer the search provider. Rotate the starting
    # point deterministically using the current 30-minute window.
    import time
    window = int(time.time() // 1800)
    start = (window * 12) % len(jobs)
    jobs = [jobs[(start + i) % len(jobs)] for i in range(min(12, len(jobs)))]

    out: list[Dict[str, str]] = []
    seen: set[str] = set()

    with DDGS() as ddgs:
        for niche, city, q in jobs:
            try:
                results = ddgs.text(q, max_results=5)
            except Exception as exc:
                print(f'Search error for {q}: {type(exc).__name__}: {exc}')
                continue

            for r in results or []:
                title = norm(r.get('title', ''))
                href = norm(r.get('href', ''))
                snippet = norm(r.get('body', ''))

                if not title or not href or not likely_business_page(title, href, snippet):
                    continue

                # Direct Instagram result: keep as a social prospect, but do not
                # pretend it is an owned website.
                is_instagram = 'instagram.com/' in href.lower()
                website = '' if is_instagram else href

                email, phone, instagram = ('', '', '')
                if website:
                    email, phone, instagram = enrich(website)

                # Search snippets sometimes reveal public contact information.
                se, sp, si = extract_contacts_from_text(f'{title} {snippet}')
                email = email or se
                phone = phone or sp
                instagram = instagram or si
                if is_instagram:
                    instagram = href

                item = {
                    'business_name': title,
                    'niche': niche,
                    'city': city,
                    'province': '',
                    'website': website,
                    'instagram': instagram,
                    'email': email,
                    'phone': phone,
                    'source_url': href,
                    'audit_score': '',
                    'audit_summary': '',
                    'outreach_status': 'NEW',
                    'outreach_at': '',
                    'wa_link': '',
                    'message_subject': '',
                    'message_body': '',
                    'notes': (
                        f'Source query: {q}; snippet: {snippet[:500]}; '
                        f'contact_found={bool(email or phone or instagram)}'
                    ),
                    'opt_out': '',
                }

                fp = fingerprint(item)
                if fp in seen:
                    continue
                seen.add(fp)
                out.append(item)

                if len(out) >= limit:
                    return out

    return out


def append_to_csv(rows: List[Dict[str, str]], path='data/prospects.csv'):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fields = [
        'business_name','niche','city','province','website','instagram','email','phone',
        'source_url','audit_score','audit_summary','outreach_status','outreach_at','wa_link',
        'message_subject','message_body','notes','opt_out'
    ]
    exists = Path(path).exists()
    with open(path, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            w.writeheader()
        w.writerows(rows)
