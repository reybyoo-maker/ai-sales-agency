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
3. Membuat email pembuka yang jujur, relevan, dan singkat.

Aturan:
- Jangan mengaku sebagai pemilik bisnis.
- Jangan berpura-pura prospect sudah tertarik.
- Jangan membuat fakta yang tidak ada pada data.
- Jangan menjanjikan hasil pasti.
- Jangan menyebut AI.
- Portfolio: {PORTFOLIO_URL}
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
            "items": {"type": "string"},
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
        key = os.getenv("GEMINI_API_KEY", "").strip()

        if not key:
            raise RuntimeError("GEMINI_API_KEY belum diisi")

        _CLIENT = genai.Client(api_key=key)

    return _CLIENT


def make_prompt(prospect: dict[str, Any]) -> str:
    return f"""
Analisis satu prospect berikut.

DATA PROSPECT:
{json.dumps(prospect, ensure_ascii=False)}

Aturan:
- Jika ini direktori, artikel, portal, aggregator, marketplace, review page,
  atau daftar bisnis:
  fit = "not_a_business_lead"
  dan score maksimal 20.

- Jika bisnis individual:
  gunakan hanya bukti yang benar-benar ada pada DATA PROSPECT.

- Semua business_lead dengan email valid tetap akan diproses.

- Buat email awal maksimal sekitar 900 karakter.

- Tujuan email:
  memperkenalkan jasa landing page dan memberi pilihan untuk lanjut lewat WhatsApp.

- Jangan mengatakan prospect sudah tertarik.

- Jangan mengarang:
  nama pemilik,
  promo,
  followers,
  layanan,
  alamat,
  statistik,
  omzet,
  atau informasi lainnya.

- Jangan menyebut AI.

- Jangan memakai:
  klaim "pasti",
  fake urgency,
  fake scarcity,
  testimonial palsu.

- Sertakan portfolio hanya SATU kali di body.

- Jangan menulis nomor WhatsApp.
  Aplikasi akan menambahkan link WhatsApp yang benar.

- Sertakan kalimat berikut persis:
  "Kalau tidak relevan, cukup balas STOP dan saya tidak akan menghubungi lagi."
""".strip()


def _parse_response(response: Any) -> dict[str, Any]:
    # SDK kadang sudah menyediakan hasil parsed.
    parsed = getattr(response, "parsed", None)

    if isinstance(parsed, dict):
        return parsed

    text = getattr(response, "text", "") or ""
    text = text.strip()

    if not text:
        raise RuntimeError("Gemini mengembalikan response kosong")

    # Fallback jika model mengembalikan JSON dalam code fence.
    if text.startswith("```"):
        text = text.replace("```json", "", 1)
        text = text.replace("```", "")
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Response Gemini bukan JSON valid: {text[:500]}"
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError("Response Gemini bukan object JSON")

    return data


def generate_prospect(prospect: dict[str, Any]) -> dict[str, Any]:
    """
    Analisis 1 prospect menggunakan generate_content().
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

    return _parse_response(response)
