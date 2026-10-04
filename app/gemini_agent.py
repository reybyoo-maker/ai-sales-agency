from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

from google import genai
from google.genai import types

from .config import MODEL, PORTFOLIO_URL

SYSTEM_PROMPT = f"""
You are the outbound sales scout for a small Indonesian landing-page agency.
Your job ends at the FIRST OUTREACH MESSAGE. Never pretend to be the human owner.
Do not claim facts that are not in supplied prospect data.
Do not use deceptive urgency, fake scarcity, fake testimonials, or impersonation.
Do not promise guaranteed results.
Write natural Indonesian, concise, respectful, and personalized.
The offer is a landing-page service. Portfolio: {PORTFOLIO_URL}
Primary goal: make a relevant business owner curious enough to continue on WhatsApp.
"""

_CLIENT: genai.Client | None = None


def get_client() -> genai.Client:
    global _CLIENT
    if _CLIENT is None:
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GEMINI_API_KEY is missing")
        _CLIENT = genai.Client(api_key=key)
    return _CLIENT


def _make_prompt(prospects: List[Dict[str, Any]]) -> str:
    return f"""
Analyze the following prospects as a batch.
Return JSON only as an ARRAY with exactly one object per prospect, in the SAME ORDER.
Each object must contain:
- score: integer 0-100
- fit: one of ["business_lead", "not_a_business_lead"]
- reasons: array of max 3 short strings
- observed_gaps: array of max 4 short strings
- contact_angle: short string
- subject: string, max 65 characters
- body: string, max 700 characters

Rules:
- Analyze every item independently.
- Reject directories, review sites, aggregators, generic city pages, and article/list pages as business leads.
- Do not invent owner names, services, followers, promotions, addresses, or contact details.
- For a directory/aggregator/article, set fit to "not_a_business_lead" and score <= 20.
- For a real business, use only evidence supplied in its data.
- Keep outreach low-pressure and permission-based.
- Mention the portfolio at most once.
- Do not include or invent a WhatsApp number. The application will append the real WhatsApp link.

PROSPECTS:
{json.dumps(prospects, ensure_ascii=False)}
"""


def _generate_batch(prompt: str) -> List[Dict[str, Any]]:
    response = get_client().models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    data = json.loads(text)
    if not isinstance(data, list):
        raise RuntimeError("Gemini batch response was not a JSON array")
    return data


def analyze_batch(prospects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not prospects:
        return []

    # One request handles the entire batch. This is the main quota-saving change.
    return _generate_batch(_make_prompt(prospects))


def analyze_prospect(prospect: Dict[str, Any]) -> Dict[str, Any]:
    results = analyze_batch([prospect])
    if not results:
        raise RuntimeError("Gemini returned no result")
    return results[0]
