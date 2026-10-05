from __future__ import annotations

import base64
import json
import re
from typing import Any

import requests

from google import genai
from google.genai import types
from pypdf import PdfReader

from .config import CV_PDF_BASE64, CV_PDF_PATH, FLYER_MAX_IMAGES, GEMINI_API_KEY, GEMINI_MODEL

def load_cv_text() -> str:
    if CV_PDF_BASE64:
        CV_PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
        CV_PDF_PATH.write_bytes(base64.b64decode(CV_PDF_BASE64))
    if not CV_PDF_PATH.exists():
        raise RuntimeError(f"CV PDF belum tersedia: {CV_PDF_PATH}")
    reader = PdfReader(str(CV_PDF_PATH))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 100:
        raise RuntimeError("CV PDF tidak memiliki teks yang cukup untuk dianalisis.")
    return text[:30000]

def load_flyer_parts(job: dict[str, Any]) -> tuple[list[Any], int]:
    raw_urls = str(job.get("flyer_image_urls", "")).strip()
    if not raw_urls:
        return [], 0

    parts: list[Any] = []
    checked = 0
    for url in [x.strip() for x in raw_urls.split("|") if x.strip()][:FLYER_MAX_IMAGES]:
        try:
            response = requests.get(
                url,
                timeout=12,
                headers={"User-Agent": "Mozilla/5.0 (compatible; BandungJobHunter/4.0)"},
            )
            response.raise_for_status()
            mime = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if not mime.startswith("image/"):
                continue
            data = response.content
            if not data or len(data) > 5_000_000:
                continue
            parts.append(types.Part.from_bytes(data=data, mime_type=mime))
            checked += 1
        except requests.RequestException:
            continue
        except Exception:
            continue
    return parts, checked

def analyze_job(job: dict[str, Any], cv_text: str, profile: dict[str, str]) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY belum diisi")
    client = genai.Client(api_key=GEMINI_API_KEY)
    schema = {
        "type": "object",
        "properties": {
            "fit_reason": {"type": "string"},
            "application_angle": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "flyer_summary": {"type": "string"},
        },
        "required": ["fit_reason", "application_angle", "subject", "body", "flyer_summary"],
    }
    prompt = f"""
Kamu adalah career application assistant.

Profil kandidat:
Nama: {profile.get('candidate_name', '')}
Headline: {profile.get('headline', '')}
WhatsApp: {profile.get('whatsapp', '')}
Project yang sedang dikembangkan: {profile.get('ai_project', '')}

CV kandidat:
{cv_text}

Data lowongan:
{json.dumps(job, ensure_ascii=False)}

Gambar/flyer lowongan:
Bila ada gambar terlampir, baca SEMUA gambar yang terlampir. Ambil hanya fakta yang benar-benar terlihat: posisi, perusahaan, lokasi, tanggal/deadline, email, nomor WhatsApp, link, benefit, syarat, dan cara melamar. Jika gambar bukan flyer lowongan, abaikan. Jangan mengarang teks yang tidak terbaca.

Aturan:
1. Jangan memakai CV sebagai filter untuk menentukan apakah lowongan boleh masuk database. Semua lowongan yang sudah lolos filter Bandung + marketing/back-office + freshness harus dibuatkan draft.
2. Gunakan CV hanya untuk memilih pengalaman/skill yang benar-benar relevan agar teks lamaran terasa personal.
3. Freelance, kontrak, hybrid, remote, part-time, internship, dan full-time boleh.
4. Jangan mengarang pengalaman, skill, nama HR, gaji, atau fakta perusahaan.
5. Buat email lamaran singkat, natural, profesional, dan spesifik ke posisi.
6. Jangan menyebut sistem otomatis. Project Agent Agency AI boleh disebut secara natural bila relevan dengan posisi, sebagai project yang sedang dikembangkan untuk membantu membuat pekerjaan lebih mudah dan terstruktur. Jangan membuat klaim teknis yang tidak ada di CV.
7. Subjek: Lamaran [Nama Posisi] | [Nama Kandidat] | Agent Agency AI Project | WA [WhatsApp]. Jaga maksimal sekitar 95 karakter; bila terlalu panjang, ringkas nama posisi/proyek tanpa menghapus identitas kandidat dan WA.
8. Body harus menyebut CV terlampir dan WhatsApp yang ada di profil. Tambahkan satu kalimat tentang project Agent Agency AI hanya bila relevan; jangan membuat email terasa seperti promosi.
9. Jangan menjamin diterima atau membuat klaim yang tidak ada di CV.
10. Jangan membuat klaim bahwa kandidat pasti cocok atau pasti diterima.
11. Jangan mengubah headline kandidat menjadi jabatan yang tidak ada di CV.
12. Project Agent Agency AI hanya boleh dipakai sebagai tambahan singkat, bukan sebagai pengalaman kerja fiktif.
13. Buat subject yang menarik tetapi profesional. Prioritaskan nama posisi, nama kandidat, dan WA. Sebut Agent Agency AI di subject hanya jika tidak membuat subject terlalu panjang.
14. flyer_summary harus merangkum fakta yang benar-benar terbaca dari flyer/gambar. Jika tidak ada flyer, tulis "Tidak ada informasi flyer yang dapat diverifikasi.".
15. Jika flyer menampilkan email/nomor kontak/deadline yang berbeda dari halaman lowongan, catat perbedaannya di flyer_summary. Jangan diam-diam mengganti data sumber.

Return JSON only.
""".strip()
    flyer_parts, flyer_checked = load_flyer_parts(job)
    contents = [prompt]
    contents.extend(flyer_parts)
    if flyer_checked:
        contents.append(
            f"Catatan sistem: {flyer_checked} gambar lowongan berhasil diambil. Baca semuanya yang relevan sebelum membuat output."
        )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0.25,
        ),
    )
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, dict):
        return parsed
    text = (getattr(response, "text", "") or "").strip()
    text = re.sub(r"^```[a-zA-Z]*", "", text)
    text = text.replace("```", "").strip()
    return json.loads(text)