"""Enrichment source: 104.com.tw (Taiwan's largest job board).

Provides skill/tool granularity the government dataset lacks. Scraped at LOW
volume only, under the academic exception; all personal data is stripped at the
boundary (see base.Posting / scrub_pii).

Endpoints (community-documented, undocumented by 104):
  * list   GET https://www.104.com.tw/jobs/search/list?keyword=&page=&order=...
  * detail GET https://www.104.com.tw/job/ajax/content/{jobId}
           -> REQUIRES header  Referer: https://www.104.com.tw/job/{jobId}

robots.txt returns 403 to plain clients, so we treat 104 as *tolerated for
low-volume educational use*, not licensed. Keep volume tiny and cache.
"""
from __future__ import annotations

import re
from typing import Iterator

from .base import BaseScraper, Posting

LIST_URL = "https://www.104.com.tw/jobs/search/list"
DETAIL_URL = "https://www.104.com.tw/job/ajax/content/{job_id}"

_SALARY_TYPE_RE = [
    ("month", re.compile(r"月薪")),
    ("year", re.compile(r"年薪")),
    ("hour", re.compile(r"時薪")),
    ("day", re.compile(r"日薪")),
]


def _salary_type(text: str | None) -> str | None:
    if not text:
        return None
    if "面議" in text:
        return "negotiable"
    for name, rx in _SALARY_TYPE_RE:
        if rx.search(text):
            return name
    return None


def _num(v) -> float | None:
    try:
        f = float(v)
        return f if f > 0 else None
    except (ValueError, TypeError):
        return None


def _join_skills(condition: dict) -> str:
    """Concatenate 104 skill/specialty/tool fields into the requirements text."""
    parts: list[str] = []
    for key in ("skill", "specialty", "tools"):
        for item in condition.get(key, []) or []:
            if isinstance(item, dict):
                parts.append(item.get("description") or item.get("name") or "")
            elif isinstance(item, str):
                parts.append(item)
    for key in ("workExp", "edu", "major", "other", "language"):
        val = condition.get(key)
        if isinstance(val, str) and val:
            parts.append(val)
    return " | ".join(p for p in parts if p) or ""


def parse_detail(job_id: str, payload: dict) -> Posting:
    """Map a 104 detail payload ({'data': {...}}) -> normalized Posting."""
    data = payload.get("data", payload)
    header = data.get("header", {}) or {}
    detail = data.get("jobDetail", {}) or {}
    condition = data.get("condition", {}) or {}

    salary_text = detail.get("salary")
    region = detail.get("addressRegion") or detail.get("jobAddrNoDesc")

    return Posting(
        source="job104",
        job_id=str(job_id),
        title=header.get("jobName"),
        company=header.get("custName"),
        description=detail.get("jobDescription"),
        requirements=_join_skills(condition),
        salary_text=salary_text,
        salary_min=_num(detail.get("salaryMin")),
        salary_max=_num(detail.get("salaryMax")),
        salary_type=_salary_type(salary_text),
        city=region,
        headcount=int(_num(detail.get("needEmp")) or 0) or None,
        education=condition.get("edu"),
        experience=condition.get("workExp"),
        category=(detail.get("jobCategory") or [{}])[0].get("description")
        if isinstance(detail.get("jobCategory"), list) else detail.get("jobCategory"),
        url=f"https://www.104.com.tw/job/{job_id}",
        posted_date=_iso(header.get("appearDate")),
    )


def _iso(yyyymmdd: str | None) -> str | None:
    if not yyyymmdd:
        return None
    s = re.sub(r"\D", "", str(yyyymmdd))
    if len(s) != 8:
        return None
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


class Job104Scraper(BaseScraper):
    source = "job104"

    def __init__(self, keyword: str = "軟體工程師", **kwargs):
        # 104 detail returns empty without a realistic browser UA.
        super().__init__(
            extra_headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                )
            },
            **kwargs,
        )
        self.keyword = keyword

    def _list_job_ids(self, max_pages: int = 2) -> list[str]:
        ids: list[str] = []
        for page in range(1, max_pages + 1):
            payload = self.get_json(
                LIST_URL,
                params={
                    "keyword": self.keyword,
                    "page": page,
                    "order": 14,   # by post date
                    "mode": "s",
                    "kwop": 7,
                },
                headers={"Referer": "https://www.104.com.tw/jobs/search/"},
            )
            for job in payload.get("data", {}).get("list", []):
                jid = job.get("jobNo") or job.get("link", {}).get("job", "").split("/")[-1]
                if jid:
                    ids.append(str(jid).split("?")[0])
        return ids

    def fetch(self, max_pages: int = 2, **kwargs) -> Iterator[Posting]:
        job_ids = self._list_job_ids(max_pages=max_pages)
        self.log.info("Found %d job ids for keyword %r", len(job_ids), self.keyword)
        for i, jid in enumerate(job_ids):
            if i >= self.max_records:
                break
            payload = self.get_json(
                DETAIL_URL.format(job_id=jid),
                headers={"Referer": f"https://www.104.com.tw/job/{jid}"},
            )
            yield parse_detail(jid, payload)
