from __future__ import annotations

import os
from pathlib import Path

TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta").strip()
LOCATION_QUERY = os.getenv("LOCATION_QUERY", "Bandung").strip()

# Freshness: only recent/open listings are queued by default.
MAX_AGE_DAYS = int(os.getenv("MAX_AGE_DAYS", "14"))
ALLOW_UNKNOWN_DATE = os.getenv("ALLOW_UNKNOWN_DATE", "false").lower() in {"1", "true", "yes", "on"}

SEARCH_RESULTS_PER_QUERY = int(os.getenv("SEARCH_RESULTS_PER_QUERY", "20"))
SEARCH_BACKENDS = ("google",)
SEARCH_DELAY_SECONDS = float(os.getenv("SEARCH_DELAY_SECONDS", "2.5"))
SEARCH_RETRY_DELAY_SECONDS = float(os.getenv("SEARCH_RETRY_DELAY_SECONDS", "8"))
FLYER_MAX_IMAGES = int(os.getenv("FLYER_MAX_IMAGES", "20"))
MAX_DISCOVERED_PER_RUN = int(os.getenv("MAX_DISCOVERED_PER_RUN", "150"))
MAX_AI_PER_RUN = int(os.getenv("MAX_AI_PER_RUN", "50"))
DAILY_SEND_LIMIT = int(os.getenv("DAILY_SEND_LIMIT", "100"))
MAX_SEND_PER_RUN = int(os.getenv("MAX_SEND_PER_RUN", "20"))
SEND_DELAY_SECONDS = int(os.getenv("SEND_DELAY_SECONDS", "45"))

# Sending is controlled by the Google Sheet status column. A row must be KIRIM.
SEND_ENABLED = os.getenv("SEND_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "REYNALDI KURNIA SONJAYA").strip()
CANDIDATE_WA = os.getenv("CANDIDATE_WA", "6287813871926").strip()
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "reybyoo@gmail.com").strip()
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "").strip()
CANDIDATE_HEADLINE = os.getenv("CANDIDATE_HEADLINE", "Leader | Mentor | Marketing Officer | Data Analyst | Digital Marketing | Promotion | Influencer").strip()
AI_PROJECT_NOTE = os.getenv("AI_PROJECT_NOTE", "Currently developing an Agent Agency AI project to simplify and improve work processes.").strip()

CV_PDF_PATH = Path(os.getenv("CV_PDF_PATH", "assets/CV.pdf")).expanduser()

# GitHub Actions secrets are limited in size. Keep backward compatibility with
# one CV_PDF_BASE64 secret, while allowing the full CV to be split across parts.
CV_PDF_BASE64 = os.getenv("CV_PDF_BASE64", "").strip()
if not CV_PDF_BASE64:
    _cv_parts = [os.getenv(f"CV_PDF_BASE64_{i}", "").strip() for i in range(1, 8)]
    if any(_cv_parts):
        if not all(_cv_parts):
            missing = [str(i) for i, value in enumerate(_cv_parts, start=1) if not value]
            raise RuntimeError(
                "CV_PDF_BASE64 parts tidak lengkap. Secret yang dibutuhkan: "
                + ", ".join(f"CV_PDF_BASE64_{i}" for i in range(1, 8))
                + ". Missing: "
                + ", ".join(f"CV_PDF_BASE64_{i}" for i in missing)
            )
        CV_PDF_BASE64 = "".join(_cv_parts)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "").strip()
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
SHEET_TAB = os.getenv("SHEET_TAB", "Job Applications").strip()

DATA_FILE = Path(os.getenv("JOBS_DATA_FILE", "data/jobs.csv"))

MARKETING_TERMS = (
    "marketing", "digital marketing", "performance marketing", "growth",
    "brand", "branding", "marketing communication", "marcom", "social media",
    "content", "content creator", "copywriter", "seo", "sem", "crm",
    "kol", "influencer", "e-commerce marketing", "trade marketing",
    "marketing executive", "marketing officer", "marketing manager",
    "sales marketing", "product marketing", "field marketing",
    "event marketing", "activation", "community", "public relations",
    "pr staff", "communication", "partnership", "business development",
)

BACK_OFFICE_TERMS = (
    "admin", "administration", "administrative", "staff administrasi",
    "back office", "finance", "accounting", "keuangan", "payroll",
    "human resources", "hr", "hrd", "recruitment", "talent acquisition",
    "purchasing", "procurement", "legal", "secretary", "secretarial",
    "personal assistant", "data entry", "data administration", "operations",
    "operational", "supply chain", "warehouse admin", "document control",
    "office support", "sales support", "project admin", "general affair",
    "ga staff", "customer service", "customer support", "customer relation",
    "staff kantor",
)

WORK_MODE_TERMS = (
    "full time", "full-time", "part time", "part-time", "freelance",
    "contract", "kontrak", "temporary", "internship", "magang",
    "hybrid", "remote", "work from home", "wfh", "on site", "onsite",
)

APPLICATION_TERMS = (
    "kirim cv", "kirim lamaran", "kirimkan cv", "send cv", "send your cv",
    "apply via email", "apply through email", "lamaran melalui email",
    "email your cv", "email cv", "kirim cv ke email", "kirim cv melalui email",
    "recruitment email", "hr email", "subject email", "subject lamaran",
)

OPEN_BLOCK_TERMS = (
    "lowongan ditutup", "closed vacancy", "posisi ditutup",
    "tidak menerima lamaran", "expired", "sudah terisi", "vacancy closed",
)

CSV_FIELDS = [
    "job_id", "found_at", "published_date", "deadline_date", "age_days",
    "job_title", "company", "company_tier", "category", "work_mode", "location",
    "source_url", "flyer_image_urls", "source_domain", "application_method", "recipient_email",
    "prospect_score", "score_reason", "candidate_headline", "ai_project_note",
    "subject", "body", "flyer_summary", "status", "sent_at", "send_error", "notes",
]