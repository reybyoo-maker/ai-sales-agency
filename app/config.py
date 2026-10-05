from __future__ import annotations

import os
from pathlib import Path

TIMEZONE = os.getenv("TIMEZONE", "Asia/Jakarta").strip()
LOCATION_QUERY = os.getenv("LOCATION_QUERY", "Bandung").strip()

# Freshness: only recent/open listings are queued by default.
MAX_AGE_DAYS = int(os.getenv("MAX_AGE_DAYS", "14"))
ALLOW_UNKNOWN_DATE = os.getenv("ALLOW_UNKNOWN_DATE", "false").lower() in {"1", "true", "yes", "on"}

SEARCH_RESULTS_PER_QUERY = int(os.getenv("SEARCH_RESULTS_PER_QUERY", "20"))
MAX_DISCOVERED_PER_RUN = int(os.getenv("MAX_DISCOVERED_PER_RUN", "150"))
MAX_AI_PER_RUN = int(os.getenv("MAX_AI_PER_RUN", "40"))
MIN_FIT_SCORE = int(os.getenv("MIN_FIT_SCORE", "55"))

# This project creates an application queue/drafts. It does not mass-send.
SEND_ENABLED = False

CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "").strip()
CANDIDATE_WA = os.getenv("CANDIDATE_WA", "6287813871926").strip()
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "reybyoo@gmail.com").strip()
CANDIDATE_HEADLINE = os.getenv("CANDIDATE_HEADLINE", "Leader | Mentor | Marketing Officer | Data Analyst | Digital Marketing | Promotion | Influencer").strip()
AI_PROJECT_NOTE = os.getenv("AI_PROJECT_NOTE", "Currently developing an Agent Agency AI project to simplify and improve work processes.").strip()

CV_PDF_PATH = Path(os.getenv("CV_PDF_PATH", "assets/CV.pdf")).expanduser()
CV_PDF_BASE64 = os.getenv("CV_PDF_BASE64", "").strip()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()

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
    "job_id", "job_title", "company", "category", "work_mode",
    "location", "source_url", "source_domain", "published_date",
    "deadline_date", "date_status", "recipient_email", "candidate_headline", "fit_score",
    "fit_reason", "subject", "body", "status", "send_approved",
    "discovered_at", "sent_at", "error", "notes",
]
