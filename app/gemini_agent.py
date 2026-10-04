from __future__ import annotations
import json
import os
from typing import Any, Dict

from google import genai
from google.genai import types

from .config import MODEL, PORTFOLIO_URL

SYSTEM_PROMPT = f"""
You are the outbound sales scout for a small Indonesian landing-page agency.
Your job ends at the FIRST OUTREACH MESSAGE. Never pretend to be the human owner.
Do not claim you know facts that are not in the supplied prospect data.
Do not use deceptive urgency, fake scarcity, fake testimonials, or impersonation.
Do not send repeated messages after a clear opt-out.
The offer is a landing page service with a portfolio at {PORTFOLIO_URL}.
Primary goal: earn permission to continue the conversation on WhatsApp.
Write natural Indonesian, concise, respectful, and personalized to the prospect's business.
"""


def client() -> genai.Client:
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        raise RuntimeError('GEMINI_API_KEY is missing')
    return genai.Client(api_key=key)


def make_outreach(prospect: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"""
Return JSON only with keys: subject, body, reason_to_contact, personalization_points.
Prospect data:
{json.dumps(prospect, ensure_ascii=False, indent=2)}

Rules:
- Subject max 65 chars.
- Body max 700 chars.
- Start with a real observation from the data, when available.
- Do NOT invent a website, follower count, promo, location, service, or owner name.
- Mention the portfolio only once if it helps credibility.
- Do not fabricate a WhatsApp number or link. The application appends the real WhatsApp link.
- Do not say 'saya lihat website...' unless a website is present in the data.
- Do not promise guaranteed sales.
"""
    response = client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type='application/json',
        ),
    )
    return json.loads(response.text)


def audit_prospect(prospect: Dict[str, Any]) -> Dict[str, Any]:
    prompt = f"""
Return JSON only with keys:
score (0-100), fit, reasons, observed_gaps, contact_angle.
The prospect is a possible buyer of landing-page services.
Data:
{json.dumps(prospect, ensure_ascii=False, indent=2)}

Be conservative. Score based only on evidence in the data.
"""
    response = client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type='application/json',
        ),
    )
    return json.loads(response.text)
