"""Primary source: 台灣就業通 / Ministry of Labor open data (data.gov.tw #44062).

Licensed under the Government Data Open License v1 (free reuse incl. commercial),
so this is the legal, reproducible spine of the pipeline.

Live JSON endpoint (whole-file download, ~tens of MB):
    https://apiservice.mol.gov.tw/OdService/download/A17000000J-030144-nkP

Field names in the source carry a Chinese suffix, e.g. "OCCU_DESC（職務名稱）".
We key on the English prefix.
"""
from __future__ import annotations

import re
from typing import Iterator
from urllib.parse import parse_qs, urlparse

from .base import BaseScraper, Posting

GOVT_JSON_URL = "https://apiservice.mol.gov.tw/OdService/download/A17000000J-030144-nkP"

# Keep the tech/IT slice that our product targets. Matched against title +
# category. Broad on purpose; tighten in production.
_IT_KEYWORDS = re.compile(
    r"(資訊|軟體|軟件|工程師|程式|系統|網路|網頁|前端|後端|全端|數據|資料|"
    r"演算法|韌體|雲端|資安|測試|developer|engineer|software|data|backend|"
    r"frontend|fullstack|devops|程序|开发|python|java)",
    re.IGNORECASE,
)

_SALARY_TYPE = {"月薪": "month", "年薪": "year", "時薪": "hour", "日薪": "day", "論件計酬": "piece"}
_CITY_RE = re.compile(r"^(.{2,3}?[市縣])")


def _en_keys(record: dict) -> dict:
    """Strip the Chinese suffix: 'OCCU_DESC（職務名稱）' -> 'OCCU_DESC'."""
    return {str(k).split("（")[0].strip(): v for k, v in record.items()}


def _to_float(v) -> float | None:
    try:
        f = float(str(v).replace(",", "").strip())
        return f if f > 0 else None
    except (ValueError, TypeError):
        return None


def _city(cityname: str | None) -> str | None:
    if not cityname:
        return None
    m = _CITY_RE.match(cityname.strip())
    return m.group(1) if m else cityname.strip()


def _iso_date(yyyymmdd: str | None) -> str | None:
    if not yyyymmdd or len(str(yyyymmdd)) != 8:
        return None
    s = str(yyyymmdd)
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def _job_id(url: str | None, fallback: str) -> str:
    if url:
        qs = parse_qs(urlparse(url).query)
        if "HIRE_ID" in qs:
            return qs["HIRE_ID"][0]
    return str(abs(hash(fallback)) % (10 ** 10))


def parse_record(record: dict) -> Posting:
    """Map one raw govt record -> normalized Posting."""
    r = _en_keys(record)
    title = r.get("OCCU_DESC")
    detail = r.get("JOB_DETAIL")
    url = r.get("URL_QUERY")
    salary_cd = (r.get("SALARYCD") or "").strip()

    requirements = " | ".join(
        x for x in [
            f"經驗:{r.get('EXPERIENCE')}" if r.get("EXPERIENCE") else None,
            f"學歷:{r.get('EDGRDESC')}" if r.get("EDGRDESC") else None,
            f"工時:{r.get('WKTIME')}" if r.get("WKTIME") else None,
        ] if x
    ) or None

    return Posting(
        source="govt",
        job_id=_job_id(url, fallback=(title or "") + (url or "")),
        title=title,
        company=r.get("COMPNAME"),
        description=detail,
        requirements=requirements,
        salary_text=salary_cd,
        salary_min=_to_float(r.get("NT_L")),
        salary_max=_to_float(r.get("NT_U")),
        salary_type=_SALARY_TYPE.get(salary_cd, "negotiable" if "面議" in salary_cd else None),
        city=_city(r.get("CITYNAME")),
        headcount=int(_to_float(r.get("JOB_PERSON")) or 0) or None,
        education=r.get("EDGRDESC"),
        experience=r.get("EXPERIENCE"),
        category=r.get("CJOB_NAME1"),
        url=url,
        posted_date=_iso_date(r.get("TRANDATE")),
    )


class GovtScraper(BaseScraper):
    source = "govt"

    def fetch(self, it_only: bool = True, **kwargs) -> Iterator[Posting]:
        self.log.info("Downloading govt open-data JSON (this is a large file)...")
        records = self.get_json(GOVT_JSON_URL)
        if isinstance(records, dict):  # some endpoints wrap in {"data": [...]}
            records = records.get("data") or records.get("result") or []
        self.log.info("Fetched %d raw records", len(records))

        emitted = 0
        for rec in records:
            if emitted >= self.max_records:
                break
            r = _en_keys(rec)
            text = f"{r.get('OCCU_DESC', '')} {r.get('CJOB_NAME1', '')} {r.get('CJOB_NAME2', '')}"
            if it_only and not _IT_KEYWORDS.search(text):
                continue
            yield parse_record(rec)
            emitted += 1
        self.log.info("Emitted %d IT postings", emitted)
