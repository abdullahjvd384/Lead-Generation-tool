"""Single point of contact with the OpenAI API.

All OpenAI-powered features (scorer_llm, outreach_llm, csv_mapper) call into
this module. It catches every SDK exception and returns None on failure, so
callers always have a clean code path to fall back to rule-based logic.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from typing import Any, Optional

logger = logging.getLogger(__name__)

# OpenAI GPT-4o mini: fast, cheap, and reliable for production use.
DEFAULT_MODEL = "gpt-4o-mini"

_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
_PLACEHOLDER_VALUES = {"", "paste_your_key_here", "your_key_here", "your_openai_key"}
_ENABLED = _API_KEY not in _PLACEHOLDER_VALUES

_client_initialized = False

# OpenAI rate limiting: stay conservative to avoid hitting rate limits.
# Using a sliding window approach.
_MAX_RPM = 60
_call_timestamps: deque[float] = deque()
_throttle_lock = threading.Lock()

# Circuit breaker: if we see this many consecutive failures, assume the key
# is exhausted/expired/invalid and stop calling OpenAI for this process's
# lifetime so we don't waste time waiting on the throttler. Callers will
# get None immediately and fall back to rule-based logic.
_MAX_CONSECUTIVE_FAILURES = 3
_consecutive_failures = 0
_circuit_open = False
_breaker_lock = threading.Lock()


def _record_success() -> None:
    global _consecutive_failures
    with _breaker_lock:
        _consecutive_failures = 0


def _record_failure(exc: Exception) -> None:
    global _consecutive_failures, _circuit_open
    with _breaker_lock:
        _consecutive_failures += 1
        if _consecutive_failures >= _MAX_CONSECUTIVE_FAILURES and not _circuit_open:
            _circuit_open = True
            logger.warning(
                "OpenAI circuit opened after %d consecutive failures. "
                "Falling back to rule-based logic for the rest of this process. "
                "Last error: %s",
                _consecutive_failures, exc,
            )


def _circuit_closed() -> bool:
    with _breaker_lock:
        return not _circuit_open


def _throttle() -> None:
    """Block until the next call would not exceed _MAX_RPM."""
    with _throttle_lock:
        now = time.monotonic()
        # Drop timestamps older than 60s.
        while _call_timestamps and now - _call_timestamps[0] > 60:
            _call_timestamps.popleft()
        if len(_call_timestamps) >= _MAX_RPM:
            wait = 60 - (now - _call_timestamps[0]) + 0.05
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
                while _call_timestamps and now - _call_timestamps[0] > 60:
                    _call_timestamps.popleft()
        _call_timestamps.append(time.monotonic())


def _ensure_client() -> bool:
    """Lazy-init the SDK so import order doesn't matter."""
    global _client_initialized
    if not _ENABLED:
        return False
    if _client_initialized:
        return True
    try:
        from openai import OpenAI
        OpenAI(api_key=_API_KEY)
        _client_initialized = True
        return True
    except Exception as exc:
        logger.warning("OpenAI SDK init failed: %s", exc)
        return False


def is_enabled() -> bool:
    """True iff a non-placeholder OPENAI_API_KEY is set AND the circuit hasn't tripped."""
    return _ENABLED and _circuit_closed()


def has_key() -> bool:
    """True iff a non-placeholder OPENAI_API_KEY is set, regardless of circuit state."""
    return _ENABLED


def circuit_open() -> bool:
    """True if the circuit breaker has tripped this process."""
    return not _circuit_closed()


def generate_json(
    prompt: str,
    *,
    schema: Optional[dict] = None,
    temperature: float = 0.2,
    model: str = DEFAULT_MODEL,
) -> Optional[dict]:
    """Run a prompt and parse the response as JSON.

    Returns None on any failure (key missing, API error, malformed JSON).
    Callers must handle None by falling back to non-LLM logic.
    """
    if not _ensure_client() or not _circuit_closed():
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=_API_KEY)
        _throttle()
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        
        text = response.choices[0].message.content.strip()
        if not text:
            return None
        result = json.loads(text)
        _record_success()
        return result
    except Exception as exc:
        logger.warning("OpenAI JSON call failed: %s", exc)
        _record_failure(exc)
        return None


def generate_text(
    prompt: str,
    *,
    temperature: float = 0.7,
    model: str = DEFAULT_MODEL,
) -> Optional[str]:
    """Run a prompt and return the raw text response, or None on failure."""
    if not _ensure_client() or not _circuit_closed():
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=_API_KEY)
        _throttle()
        
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        
        text = response.choices[0].message.content.strip()
        if text:
            _record_success()
            return text
        return None
    except Exception as exc:
        logger.warning("OpenAI text call failed: %s", exc)
        _record_failure(exc)
        return None
