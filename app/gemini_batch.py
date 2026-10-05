from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

from .config import (
    MODEL,
    OFFER_NAME,
    SAMPLE_LEADS,
    STARTER_PRICE,
    TARGET_COUNTRY,
)


SYSTEM = f"""
Kamu adalah AI sales researcher untuk jasa B2B Lead Database.

PRODUK YANG DIJUAL:
{OFFER_NAME}

PENAWARAN:
- Sample gratis: {SAMPLE_LEADS} lead
- Paket awal: Rp{STARTER_PRICE}
- Target negara utama: {TARGET_COUNTRY}

TUGAS UTAMA:
Menganalisis calon buyer yang ditemukan melalui intent discovery
dan menentukan apakah mereka kemungkinan membutuhkan jasa B2B
lead research, lead generation, email list building,
data enrichment, prospect research, atau appointment-setting support.

Kamu BUKAN lagi menjual landing page.

Jangan membahas jasa landing page kecuali informasi tersebut
secara eksplisit ada dalam data dan benar-benar relevan.

ATURAN KEJUJURAN:
- Jangan mengarang nama orang.
- Jangan mengarang jabatan.
- Jangan mengarang nama perusahaan.
- Jangan mengarang budget.
- Jangan mengarang jumlah karyawan.
- Jangan mengarang jumlah customer.
- Jangan mengarang layanan.
- Jangan mengarang email.
- Jangan mengarang fakta dari website.
- Jangan mengaku sebagai bagian dari perusahaan prospect.
- Jangan menjanjikan hasil pasti.
- Jangan menggunakan fake urgency.
- Jangan menggunakan fake scarcity.
- Jangan menggunakan testimonial palsu.
- Jangan menyebut AI kepada prospect.

PRINSIP OUTREACH:
- Personal.
- Singkat.
- Profesional.
- Tidak memaksa.
- Berdasarkan intent yang benar-benar ditemukan.
- Fokus pada kebutuhan prospect.
- Tawarkan sample kecil terlebih dahulu.
- CTA utama: meminta izin mengirim sample.
""".strip()


_CLIENT: genai.Client | None = None


def client() -> genai.Client:
    global _CLIENT

    if _CLIENT is None:
        key = os.getenv(
            "GEMINI_API_KEY",
            "",
        ).strip()

        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY belum diisi"
            )

        _CLIENT = genai.Client(
            api_key=key
        )

    return _CLIENT


def make_prompt(
    prospect: dict[str, Any],
) -> str:

    evidence = {
        "business_name": prospect.get(
            "business_name",
            "",
        ),
        "niche": prospect.get(
            "niche",
            "",
        ),
        "city": prospect.get(
            "city",
            "",
        ),
        "province": prospect.get(
            "province",
            "",
        ),
        "website": prospect.get(
            "website",
            "",
        ),
        "email": prospect.get(
            "email",
            "",
        ),
        "website_title": prospect.get(
            "website_title",
            "",
        ),
        "website_text": prospect.get(
            "website_text",
            "",
        )[:6000],

        "intent_type": prospect.get(
            "intent_type",
            "",
        ),
        "intent_source": prospect.get(
            "intent_source",
            "",
        ),
        "intent_url": prospect.get(
            "intent_url",
            "",
        ),
        "intent_title": prospect.get(
            "intent_title",
            "",
        ),
        "intent_date": prospect.get(
            "intent_date",
            "",
        ),
        "intent_budget": prospect.get(
            "intent_budget",
            "",
        ),
        "intent_score": prospect.get(
            "intent_score",
            "",
        ),

        "notes": prospect.get(
            "notes",
            "",
        )[:1500],
    }

    return f"""
Analisis calon buyer berikut.

DATA:
{json.dumps(
    evidence,
    ensure_ascii=False,
)}

TUJUAN:
Tentukan apakah prospect ini merupakan calon pembeli yang
masuk akal untuk jasa B2B Lead Database.

==================================================
PENILAIAN
==================================================

Score 90-100:
Intent sangat kuat.
Contohnya secara eksplisit sedang mencari:
- B2B leads
- lead generation
- email list building
- prospect research
- data enrichment
- lead researcher
- sales research
- appointment setting

Score 75-89:
Sangat relevan tetapi intent tidak sekuat kategori di atas.

Score 50-74:
Mungkin relevan tetapi bukti kebutuhan lemah.

Score di bawah 50:
Jangan diprioritaskan.

Jika sumber ternyata:
- direktori
- aggregator
- artikel
- berita
- marketplace
- review page
- halaman generik
- halaman yang bukan perusahaan/client
maka:

fit = "not_a_business_lead"

dan score maksimal 20.

==================================================
ANALISIS INTENT
==================================================

Perhatikan:

1. Apa sebenarnya kebutuhan yang tertulis?
2. Apakah kebutuhan tersebut cocok dengan produk B2B Lead Database?
3. Apakah sumbernya terlihat seperti job/request nyata?
4. Apakah ada budget?
5. Apakah ada tanggal/posting yang masuk akal?
6. Apakah ada informasi perusahaan?
7. Apakah ada website resmi?
8. Apakah email yang tersedia terlihat sebagai email bisnis?

Jangan menebak jika informasi tidak tersedia.

==================================================
EMAIL
==================================================

Buat email cold outreach yang berdasarkan intent.

Jangan pura-pura tahu nama owner jika nama owner tidak tersedia.

Kalau tidak ada nama orang, gunakan:

"Halo Tim [nama perusahaan],"

atau sapaan umum yang natural.

Email harus:

- sekitar 500-900 karakter
- bahasa Indonesia
- profesional
- natural
- tidak terlalu formal
- tidak bertele-tele
- tidak memakai emoji berlebihan
- tidak membahas landing page
- tidak menyebut "AI"
- tidak menjanjikan hasil
- tidak memaksa

EMAIL HARUS MENYEBUTKAN KEBUTUHAN YANG TERLIHAT
DARI INTENT BILA MEMANG ADA.

Contoh angle:

"Saya melihat tim Anda sedang mencari bantuan untuk B2B lead generation."

atau:

"Saya melihat kebutuhan terkait email list building yang sedang dibuka."

Jangan mengatakan hal tersebut bila tidak terdapat
bukti dalam data.

Kemudian tawarkan:

"Kalau relevan, saya bisa kirim sample 10 lead terlebih dahulu
agar tim Anda bisa melihat format dan kualitas datanya."

CTA utama:

"Kalau berkenan, saya kirim sample-nya."

Tambahkan:

"Kalau tidak relevan, balas STOP dan saya tidak akan
menghubungi lagi."

Jangan membuat nomor WhatsApp.

Jangan membuat link palsu.

Jangan membuat portfolio palsu.

==================================================
OUTPUT
==================================================

Return JSON object dengan field:

score
fit
observed_gaps
contact_angle
subject
body

fit hanya boleh:
- business_lead
- not_a_business_lead

observed_gaps:
maksimal 4 item.

subject:
maksimal 65 karakter.

body:
maksimal 900 karakter.

Hanya JSON.
""".strip()


def _parse(
    response: Any,
) -> dict[str, Any]:

    parsed = getattr(
        response,
        "parsed",
        None,
    )

    if isinstance(
        parsed,
        dict,
    ):
        return parsed

    text = (
        getattr(
            response,
            "text",
            "",
        )
        or ""
    ).strip()

    if not text:
        raise RuntimeError(
            "Gemini mengembalikan response kosong"
        )

    if text.startswith("```"):
        text = text.replace(
            "```json",
            "",
            1,
        )

        text = text.replace(
            "```",
            "",
        ).strip()

    data = json.loads(
        text
    )

    if not isinstance(
        data,
        dict,
    ):
        raise RuntimeError(
            "Response Gemini bukan object JSON"
        )

    return data


def generate_prospect(
    prospect: dict[str, Any],
) -> dict[str, Any]:

    schema = {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
            },
            "fit": {
                "type": "string",
                "enum": [
                    "business_lead",
                    "not_a_business_lead",
                ],
            },
            "observed_gaps": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "maxItems": 4,
            },
            "contact_angle": {
                "type": "string",
            },
            "subject": {
                "type": "string",
            },
            "body": {
                "type": "string",
            },
        },
        "required": [
            "score",
            "fit",
            "observed_gaps",
            "contact_angle",
            "subject",
            "body",
        ],
    }

    response = client().models.generate_content(
        model=MODEL,
        contents=make_prompt(
            prospect
        ),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0.2,
        ),
    )

    return _parse(
        response
    )


def analyze_prospect(
    prospect: dict[str, Any],
) -> dict[str, Any]:

    return generate_prospect(
        prospect
    )
