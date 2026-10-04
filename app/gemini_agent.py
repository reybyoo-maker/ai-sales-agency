from __future__ import annotations

import json
import os
import random
import re
import time
from typing import Any, Dict

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
_LAST_CALL_MONOTONIC = 0.0
MIN_SECONDS_BETWEEN_REQUESTS = float(os.getenv("GEMINI_MIN_SECONDS_BETWEEN_REQUESTS", "15"))


def get_client() -> genai.Client:
    global _CLIENT
    if _CLIENT is None:
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("GEMINI_API_KEY is missing")
        _CLIENT = genai.Client(api_key=key)
    return _CLIENT


def _rate_limit_wait() -> None:
    global _LAST_CALL_MONOTONIC
    if _LAST_CALL_MONOTONIC:
        wait = MIN_SECONDS_BETWEEN_REQUESTS - (time.monotonic() - _LAST_CALL_MONOTONIC)
        if wait > 0:
            print(f"Gemini pacing: sleeping {wait:.1f}s")
            time.sleep(wait)


def _retry_seconds(message: str, default: float) -> float:
    m = re.search(r"retry(?: in|Delay of)\s+([0-9]+(?:\.[0-9]+)?)s", message, re.I)
    if not m:
        m = re.search(r"retryDelay[^0-9]*([0-9]+(?:\.[0-9]+)?)s", message, re.I)
    if m:
        return min(max(float(m.group(1)) + 1.0, default), 90.0)
    return default


def _generate_json(prompt: str) -> Dict[str, Any]:
    global _LAST_CALL_MONOTONIC
    last_error: Exception | None = None

    for attempt in range(4):
        try:
            _rate_limit_wait()
            _LAST_CALL_MONOTONIC = time.monotonic()
            response = get_client().models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )
            text = (response.text or "").strip()
            if not text:
                raise RuntimeError("Gemini returned an empty response")
            result = json.loads(text)
            if not isinstance(result, dict):
                raise RuntimeError("Gemini response was not a JSON object")
            return result
        except Exception as exc:
            last_error = exc
            message = str(exc)
            retryable = any(code in message for code in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "500"))
            if not retryable or attempt >= 3:
                raise
            delay = _retry_seconds(message, 35.0 + attempt * 10.0)
            delay += random.uniform(0, 3)
            print(f"Gemini temporary error; retrying in {delay:.1f}s: {message[:180]}")
            time.sleep(delay)

    assert last_error is not None
    raise last_error


def analyze_prospect(prospect: Dict[str, Any]) -> Dict[str, Any]:
    """One Gemini call returns both audit + first-touch message.

    Combining these two operations halves API requests versus calling audit and
    outreach separately, which is important on the free request-per-minute quota.
    """
    prompt = f"""
Return JSON only with these keys:
score (integer 0-100)
fit (string)
reasons (array of strings, max 3)
observed_gaps (array of strings, max 4)
contact_angle (string)
subject (string, max 65 chars)
body (string, max 700 chars)

Prospect data:
{json.dumps(prospect, ensure_ascii=False, indent=2)}

Rules:
- Score only from evidence in the prospect data; be conservative.
- Reject directories, review sites, aggregators, generic city pages, and article/list pages as business leads.
- Do not invent owner names, services, followers, promotions, addresses, or contact details.
- If the source is a directory/aggregator instead of a specific business, set fit to "not_a_business_lead" and score <= 20.
- For a valid business, mention one concrete observation from the data when possible.
- Keep the first outreach low-pressure and permission-based.
- Mention the portfolio at most once.
- Do not fabricate or modify the WhatsApp number. The application adds the real WhatsApp link.
"""
    return _generate_json(prompt)
