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
Tugasmu: menilai apakah data adalah bisnis individual dan membuat email pembuka yang jujur, relevan,
dan singkat. Jangan mengaku sebagai pemilik bisnis, jangan berpura-pura prospect sudah tertarik,
dan jangan membuat fakta yang tidak ada pada data. Jangan menjanjikan hasil pasti.
Portfolio: {PORTFOLIO_URL}
""".strip()

SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "fit": {"type": "string", "enum": ["business_lead", "not_a_business_lead"]},
        "observed_gaps": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "contact_angle": {"type": "string"},
        "subject": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["score", "fit", "observed_gaps", "contact_angle", "subject", "body"],
    "additionalProperties": False,
}


def client() -> genai.Client:
    global _CLIENT
    if _CLIENT is None:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GEMINI_API_KEY belum diisi")
        _CLIENT = genai.Client(api_key=key)
    return _CLIENT


def make_request(prospect: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""
Analisis satu prospect berikut.

DATA PROSPECT:
{json.dumps(prospect, ensure_ascii=False)}

Aturan:
- Jika ini direktori, artikel, portal, aggregator, marketplace, review page, atau daftar bisnis, fit=not_a_business_lead dan score maksimal 20.
- Jika bisnis individual, gunakan bukti yang ada saja.
- Score bukan filter outreach; semua business_lead dengan email valid tetap akan dihubungi.
- Buat email awal maksimal sekitar 900 karakter.
- Tujuan email: memperkenalkan jasa landing page dan memberi pilihan untuk lanjut lewat WhatsApp.
- Jangan mengatakan prospect sudah tertarik.
- Jangan mengarang nama pemilik, promo, followers, layanan, alamat, atau statistik.
- Jangan menyebut AI.
- Jangan memakai klaim "pasti", fake urgency, fake scarcity, atau testimonial palsu.
- Sertakan portfolio hanya sekali di body.
- Jangan menulis nomor WhatsApp; aplikasi akan menambahkan link WhatsApp yang benar.
- Sertakan kalimat: "Kalau tidak relevan, cukup balas STOP dan saya tidak akan menghubungi lagi."
""".strip()

    req = {
        "contents": [{"parts": [{"text": prompt}], "role": "user"}],
        "config": {
            "system_instruction": {"parts": [{"text": SYSTEM}]},
            "response_mime_type": "application/json",
            "response_schema": SCHEMA,
        },
    }
    return req


def create_batch(prospects: list[dict[str, Any]], display_name: str = "ai-sales-agency"):
    src = [make_request(p) for p in prospects]
    return client().batches.create(model=MODEL, src=src, config={"display_name": display_name})


def get_batch(name: str):
    return client().batches.get(name=name)


def parse_inline_results(batch_job) -> list[dict[str, Any]]:
    dest = getattr(batch_job, "dest", None)
    responses = getattr(dest, "inlined_responses", None) if dest else None
    if not responses:
        raise RuntimeError("Batch selesai tetapi hasil inline tidak ditemukan")
    out: list[dict[str, Any]] = []
    for item in responses:
        if getattr(item, "error", None):
            raise RuntimeError(f"Batch item error: {item.error}")
        response = getattr(item, "response", None)
        text = getattr(response, "text", "") if response else ""
        if not text:
            raise RuntimeError("Salah satu hasil batch kosong")
        data = json.loads(text)
        if not isinstance(data, dict):
            raise RuntimeError("Hasil batch bukan object JSON")
        out.append(data)
    return out
