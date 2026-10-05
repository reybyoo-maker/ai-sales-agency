from __future__ import annotations

import base64
import json
import re
from typing import Any

from google import genai
from google.genai import types
from pypdf import PdfReader

from .config import CV_PDF_BASE64, CV_PDF_PATH, GEMINI_API_KEY, GEMINI_MODEL, MIN_FIT_SCORE

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

def analyze_job(job: dict[str, Any], cv_text: str, profile: dict[str, str]) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY belum diisi")
    client = genai.Client(api_key=GEMINI_API_KEY)
    schema = {
        "type": "object",
        "properties": {
            "fit_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "fit_reason": {"type": "string"},
            "application_angle": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["fit_score", "fit_reason", "application_angle", "subject", "body"],
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

Aturan:
1. Nilai kecocokan 0-100 hanya berdasarkan CV dan data lowongan.
2. Prioritaskan semua aspek marketing. Terima juga back office jika benar-benar cocok dengan CV.
3. Freelance, kontrak, hybrid, remote, part-time, internship, dan full-time boleh.
4. Jangan mengarang pengalaman, skill, nama HR, gaji, atau fakta perusahaan.
5. Buat email lamaran singkat, natural, profesional, dan spesifik ke posisi.
6. Jangan menyebut sistem otomatis. Project Agent Agency AI boleh disebut secara natural bila relevan dengan posisi, sebagai project yang sedang dikembangkan untuk membantu membuat pekerjaan lebih mudah dan terstruktur. Jangan membuat klaim teknis yang tidak ada di CV.
7. Subjek: Lamaran [Nama Posisi] | [Nama Kandidat] | Agent Agency AI Project | WA [WhatsApp]. Jaga maksimal sekitar 95 karakter; bila terlalu panjang, ringkas nama posisi/proyek tanpa menghapus identitas kandidat dan WA.
8. Body harus menyebut CV terlampir dan WhatsApp yang ada di profil. Tambahkan satu kalimat tentang project Agent Agency AI hanya bila relevan; jangan membuat email terasa seperti promosi.
9. Jangan menjamin diterima atau membuat klaim yang tidak ada di CV.
10. Kandidat dengan fit_score >= {MIN_FIT_SCORE} masuk antrean READY.
11. Jangan mengubah headline kandidat menjadi jabatan yang tidak ada di CV.
12. Project Agent Agency AI hanya boleh dipakai sebagai tambahan singkat, bukan sebagai pengalaman kerja fiktif.

Return JSON only.
""".strip()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
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