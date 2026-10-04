from __future__ import annotations

import hashlib
import re
import time
from urllib.parse import urlparse

from ddgs import DDGS

from .web import clean_email, clean_phone, snapshot


PROVINCES = [
    "Aceh",
    "Sumatera Utara",
    "Sumatera Barat",
    "Riau",
    "Kepulauan Riau",
    "Jambi",
    "Sumatera Selatan",
    "Bengkulu",
    "Lampung",
    "Bangka Belitung",
    "Banten",
    "DKI Jakarta",
    "Jawa Barat",
    "Jawa Tengah",
    "DI Yogyakarta",
    "Jawa Timur",
    "Bali",
    "Nusa Tenggara Barat",
    "Nusa Tenggara Timur",
    "Kalimantan Barat",
    "Kalimantan Tengah",
    "Kalimantan Selatan",
    "Kalimantan Timur",
    "Kalimantan Utara",
    "Sulawesi Utara",
    "Sulawesi Tengah",
    "Sulawesi Selatan",
    "Sulawesi Tenggara",
    "Gorontalo",
    "Sulawesi Barat",
    "Maluku",
    "Maluku Utara",
    "Papua",
    "Papua Barat",
    "Papua Selatan",
    "Papua Tengah",
    "Papua Pegunungan",
    "Papua Barat Daya",
]


NICHES = [
    "cafe",
    "coffee shop",
    "barbershop",
    "salon",
    "gym",
    "fitness",
    "klinik kecantikan",
    "spa",
    "laundry",
    "wedding organizer",
    "event organizer",
    "fotografer",
    "videografer",
    "studio foto",
    "travel agent",
    "tour travel",
    "kursus",
    "les privat",
    "bengkel",
    "car detailing",
    "MUA",
    "catering",
    "bakery",
    "fashion boutique",
    "toko bunga",
    "property agent",
    "jasa interior",
    "kontraktor",
    "cleaning service",
    "pet shop",
    "klinik gigi",
    "dealer mobil",
    "sewa mobil",
    "rental mobil",
]


# Domain yang hampir pasti bukan bisnis individual target kita.
BLOCKED = {
    "tripadvisor.com",
    "fresha.com",
    "yelp.com",
    "wanderlog.com",
    "bridestory.com",
    "tempat.info",
    "rekomended.com",
    "idalamat.com",
    "indonesiaknowledge.com",
    "beautynailhairsalons.com",
    "laundry.co.id",
    "laundryindonesia.com",
    "barberhead.com",
    "localoria.com",
    "yellowpages.co.id",
    "indotrading.com",
    "wikipedia.org",
    "kompas.com",
    "detik.com",
    "tempo.co",
    "tokopedia.com",
    "shopee.co.id",
    "lazada.co.id",
    "traveloka.com",
    "gofood.co.id",
    "grab.com",
    "facebook.com",
    "youtube.com",
    "tiktok.com",
    "linkedin.com",
    "instagram.com",
    "linktr.ee",
    "seo-for-jobs.info",
    "superlocal.id",
    "cari.co",
    "menukuliner.net",
    "qraved.com",
}


BAD_TITLE = (
    "rekomendasi",
    "direktori",
    "directory",
    "best ",
    "daftar ",
    "list ",
    "near me",
    "review",
    "reviews",
    "ranking",
    "top ",
    "harga ",
    "artikel",
    "news",
    "berita",
    "wikipedia",
    "lowongan",
    "job",
    "jobs",
)


BAD_TEXT = (
    "directory",
    "direktori",
    "list of",
    "daftar 10",
    "daftar 20",
    "rekomendasi",
    "comparison",
    "compare prices",
    "review tempat",
    "lowongan kerja",
    "vacancy",
    "loker",
)


def norm(v: str) -> str:
    return re.sub(r"\s+", " ", v or "").strip()


def dom(url: str) -> str:
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


def blocked(url: str) -> bool:
    d = dom(url)

    if not d:
        return True

    return any(
        d == x or d.endswith("." + x)
        for x in BLOCKED
    )


def likely_business(
    title: str,
    href: str,
    body: str,
) -> bool:

    if not href.startswith(("http://", "https://")):
        return False

    if blocked(href):
        return False

    if not title.strip():
        return False

    title_lower = title.lower()
    body_lower = body.lower()

    if any(x in title_lower for x in BAD_TITLE):
        return False

    if any(x in body_lower for x in BAD_TEXT):
        return False

    # Hindari URL yang jelas merupakan halaman directory/listing.
    path = urlparse(href).path.lower()

    bad_path_words = (
        "/directory",
        "/direktori",
        "/listing",
        "/category/",
        "/kategori/",
        "/tag/",
        "/search",
        "/jobs/",
        "/lowongan/",
        "/blog/",
        "/artikel/",
    )

    if any(x in path for x in bad_path_words):
        return False

    return True


def extract_email(text: str) -> str:
    if not text:
        return ""

    match = re.search(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        text,
    )

    if not match:
        return ""

    return clean_email(match.group(0))


def extract_phone(text: str) -> str:
    if not text:
        return ""

    match = re.search(
        r"(?:\+62|62|0)(?:[\s().-]*\d){9,14}",
        text,
    )

    if not match:
        return ""

    return clean_phone(match.group(0))


def extract_instagram(links: list[str] | None) -> str:
    if not links:
        return ""

    for link in links:
        if "instagram.com/" in link.lower():
            return link.strip()

    return ""


def fingerprint(p: dict) -> str:
    s = "|".join(
        (p.get(k) or "")
        .strip()
        .lower()
        .rstrip("/")
        for k in (
            "business_name",
            "website",
            "instagram",
            "email",
            "phone",
        )
    )

    return hashlib.sha1(
        s.encode("utf-8")
    ).hexdigest()


def build_jobs():
    """
    Buat banyak variasi query supaya sumber prospect tidak
    hanya bergantung pada satu pola pencarian.
    """

    jobs = []

    for province in PROVINCES:
        for niche in NICHES:

            jobs.append(
                (
                    province,
                    niche,
                    f'"{niche}" "{province}" Indonesia '
                    f'official website contact',
                )
            )

            jobs.append(
                (
                    province,
                    niche,
                    f'"{niche}" "{province}" Indonesia '
                    f'email WhatsApp',
                )
            )

            jobs.append(
                (
                    province,
                    niche,
                    f'"{niche}" "{province}" Indonesia '
                    f'kontak',
                )
            )

    return jobs


def discover(limit: int = 30) -> list[dict]:
    """
    Cari prospect bisnis individual.

    limit:
        jumlah maksimum prospect VALID yang dikembalikan.
    """

    if limit <= 0:
        return []

    jobs = build_jobs()

    # Rotasi query berdasarkan waktu supaya setiap run
    # tidak mencari kombinasi yang sama terus-menerus.
    window = int(time.time() // 1800)

    # Ambil 20 query tiap run.
    query_count = min(
        20,
        len(jobs),
    )

    start = (
        window * query_count
    ) % len(jobs)

    selected = [
        jobs[
            (start + i) % len(jobs)
        ]
        for i in range(query_count)
    ]

    print(
        f"Discovery query count: "
        f"{len(selected)}"
    )

    out: list[dict] = []
    seen: set[str] = set()

    with DDGS() as ddgs:

        for query_index, (
            province,
            niche,
            query,
        ) in enumerate(
            selected,
            start=1,
        ):

            print(
                f"[Discovery {query_index}/"
                f"{len(selected)}] "
                f"{query}"
            )

            try:
                results = ddgs.text(
                    query,
                    max_results=10,
                )

            except Exception as exc:
                print(
                    f"DISCOVERY ERROR "
                    f"{type(exc).__name__}: {exc}"
                )
                continue

            for r in results or []:

                title = norm(
                    r.get("title", "")
                )

                href = norm(
                    r.get("href", "")
                )

                snippet = norm(
                    r.get("body", "")
                )

                if not likely_business(
                    title,
                    href,
                    snippet,
                ):
                    continue

                # Coba ambil email + phone langsung dari snippet.
                email = extract_email(
                    snippet
                )

                phone = extract_phone(
                    snippet
                )

                instagram = ""

                # Hanya buka website jika email belum
                # tersedia dari hasil search.
                if not email:

                    try:
                        snap = snapshot(
                            href
                        )

                    except Exception as exc:
                        print(
                            f"SNAPSHOT ERROR "
                            f"{href}: "
                            f"{type(exc).__name__}: {exc}"
                        )
                        continue

                    if not snap.get("ok"):
                        continue

                    email = (
                        (snap.get("emails") or [""])[0]
                        or ""
                    )

                    phone = (
                        phone
                        or (
                            (snap.get("phones") or [""])[0]
                            if snap.get("phones")
                            else ""
                        )
                    )

                    instagram = extract_instagram(
                        snap.get("links") or []
                    )

                # Kalau email masih kosong, prospect
                # belum cukup layak untuk outreach.
                if not email:
                    continue

                email = clean_email(
                    email
                )

                if not email:
                    continue

                if phone:
                    phone = clean_phone(
                        phone
                    )

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
                    "notes": (
                        f"Source query: {query}; "
                        f"snippet: {snippet[:500]}"
                    ),
                    "opt_out": "",
                }

                fp = fingerprint(item)

                if fp in seen:
                    continue

                seen.add(fp)
                out.append(item)

                print(
                    f"FOUND: {title} | "
                    f"{email}"
                )

                if len(out) >= limit:
                    print(
                        f"Discovery target reached: "
                        f"{limit}"
                    )
                    return out

    print(
        f"Discovery finished: "
        f"{len(out)} valid prospects"
    )

    return out
