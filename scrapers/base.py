"""Base scraper: a small, polite HTTP client + the normalized posting schema.

Politeness (data-ethics requirement of the project):
  * one request at a time per host, with a configurable min delay + jitter
  * exponential backoff on 429 / 5xx / transport errors
  * an honest, identifying User-Agent
  * a hard cap on the number of records pulled per run

PII handling: personal data (recruiter name / email / phone) is never stored.
Free-text fields are additionally scrubbed of emails and phone numbers.
"""
from __future__ import annotations

import abc
import logging
import random
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Iterator

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from . import settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Taiwan mobile / landline-ish digit runs; deliberately broad to over-scrub.
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?886[-\s]?|0)\d{1,2}[-\s]?\d{3,4}[-\s]?\d{3,4}(?!\d)")


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def scrub_pii(text: str | None) -> str | None:
    """Remove emails and phone numbers from free text before persisting."""
    if not text:
        return text
    text = _EMAIL_RE.sub("[email-removed]", text)
    text = _PHONE_RE.sub("[phone-removed]", text)
    return text


@dataclass
class Posting:
    """Normalized, PII-free job posting (the bronze record)."""

    source: str
    job_id: str
    title: str | None = None
    company: str | None = None
    description: str | None = None
    requirements: str | None = None
    salary_text: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_type: str | None = None  # month | year | hour | negotiable | None
    city: str | None = None
    headcount: int | None = None
    education: str | None = None
    experience: str | None = None
    category: str | None = None
    url: str | None = None
    posted_date: str | None = None  # ISO date
    fetched_at: str = field(default_factory=utcnow_iso)

    def __post_init__(self):
        self.description = scrub_pii(self.description)
        self.requirements = scrub_pii(self.requirements)

    @property
    def key(self) -> str:
        """Stable lake key, e.g. govt/govt-12345."""
        return f"{self.source}/{self.source}-{self.job_id}"

    def to_dict(self) -> dict:
        return asdict(self)


class BaseScraper(abc.ABC):
    """Polite HTTP scraper. Subclasses implement ``fetch()`` yielding Postings."""

    #: short source name, used in lake paths and the ``source`` field
    source: str = "base"

    def __init__(
        self,
        delay: float | None = None,
        max_records: int | None = None,
        extra_headers: dict | None = None,
    ):
        self.delay = settings.SCRAPE_DELAY_SECONDS if delay is None else delay
        self.max_records = settings.SCRAPE_MAX_RECORDS if max_records is None else max_records
        self.log = logging.getLogger(self.source)
        headers = {"User-Agent": settings.SCRAPE_USER_AGENT, "Accept": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        self.client = httpx.Client(headers=headers, timeout=30.0, follow_redirects=True)
        self._last_request = 0.0

    # --- politeness ---------------------------------------------------------
    def _throttle(self):
        elapsed = time.monotonic() - self._last_request
        wait = self.delay - elapsed
        if wait > 0:
            time.sleep(wait + random.uniform(0, 0.5))  # jitter
        self._last_request = time.monotonic()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def get_json(self, url: str, params: dict | None = None, headers: dict | None = None) -> dict:
        """GET a URL and return parsed JSON, throttled + retried with backoff."""
        self._throttle()
        self.log.info("GET %s params=%s", url, params or {})
        resp = self.client.get(url, params=params, headers=headers)
        if resp.status_code in (429, 500, 502, 503, 504):
            resp.raise_for_status()  # triggers retry
        resp.raise_for_status()
        return resp.json()

    # --- contract -----------------------------------------------------------
    @abc.abstractmethod
    def fetch(self, **kwargs) -> Iterator[Posting]:
        """Yield normalized, PII-free Postings from the live source."""
        raise NotImplementedError

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
