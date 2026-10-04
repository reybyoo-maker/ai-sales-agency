from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types

from .config import MODEL, PORTFOLIO_URL

_CLIENT: genai.Client | None = None


SYSTEM = f"""
Kamu adalah sales scout untuk agency landing page Indonesia.

Tugasmu:
1. Menilai apakah data prospect adalah bisnis individual.
2. Menentukan kualitas prospect.
3. Membuat email pembuka yang jujur, relevan, natural, dan singkat.

Aturan penting:
- Jangan mengaku sebagai pemilik bisnis.
- Jangan berpura-pura prospect sudah tertarik.
- Jangan membuat fakta yang tidak ada pada data.
- Jangan menjanjikan hasil pasti.
- Jangan menyebut AI.
- Jangan menggunakan fake urgency.
- Jangan menggunakan fake scarcity.
- Jangan membuat testimonial palsu.

Portfolio:
{PORTFOLIO_URL}
""".strip()


SCHEMA = {
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
                "type": "string",
            },
            "maxItems": 3,
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

    return f"""
Analisis satu prospect berikut.

DATA PROSPECT:
{json.dumps(
    prospect,
    ensure_ascii=False,
)}

ATURAN PENILAIAN:

1. Jika data merupakan:
- direktori
- aggregator
- portal
- marketplace
- artikel
- halaman review
- listing umum
- website lowongan kerja
- halaman yang bukan bisnis individual

maka:

fit = "not_a_business_lead"

dan score maksimal 20.

2. Jika merupakan bisnis individual:
gunakan hanya informasi yang benar-benar
terdapat pada DATA PROSPECT.

3. Jangan mengarang:
- nama pemilik
- nama contact person
- alamat
- followers
- promo
- layanan yang tidak tercantum
- omzet
- statistik
- testimonial
- jumlah pelanggan
- pencapaian bisnis.

4. Buat email pembuka yang:
- natural
- profesional
- singkat
- relevan dengan niche
- tidak terlalu memuji
- tidak terdengar seperti spam massal
- tidak mengklaim hasil pasti.

5. Tujuan email:
memperkenalkan jasa landing page
dan membuka kesempatan berdiskusi.

6. Jangan menggunakan kalimat:
"saya tertarik dengan layanan Anda"
kecuali memang didukung oleh data.

7. Jangan mengatakan:
- website Anda buruk
- website Anda jelek
- pasti meningkatkan penjualan
- dijamin mendapatkan lebih banyak pelanggan

8. Gunakan bukti yang ada pada prospect.

9. Buat email maksimal sekitar 900 karakter.

10. Sertakan portfolio SATU kali saja.

Portfolio:
{PORTFOLIO_URL}

11. Jangan membuat bagian:
"Lanjut via WhatsApp"

Aplikasi akan menambahkan link WhatsApp
secara otomatis.

12. Jangan menulis nomor WhatsApp.

13. Sertakan kalimat berikut:

"Kalau tidak relevan, cukup balas STOP dan saya tidak akan menghubungi lagi."

14. Jangan menyebut AI.

OUTPUT:
- score
- fit
- observed_gaps
- contact_angle
- subject
- body
""".strip()


def _parse_response(
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

    try:
        data = json.loads(text)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Response Gemini bukan JSON valid: "
            f"{text[:500]}"
        ) from exc

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
    """
    Analisis satu prospect menggunakan
    Gemini generate_content().

    Tidak menggunakan Gemini Batch API.
    """

    response = client().models.generate_content(
        model=MODEL,
        contents=make_prompt(prospect),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            response_mime_type="application/json",
            response_json_schema=SCHEMA,
            temperature=0.2,
        ),
    )

    return _parse_response(
        response
    )
