"""Ingestion entrypoint: land normalized postings into the lake.

Two modes:
  * OFFLINE (default): replay committed raw samples in data/sample_data/<source>.json
    through the SAME parsers as live scraping -> reproducible demo, no network.
  * LIVE (--live): run the real scraper against the source.

Usage:
    python -m scrapers.pipeline_to_lake --source govt
    python -m scrapers.pipeline_to_lake --source govt --live
    python -m scrapers.pipeline_to_lake --source job104 --live --max 50
"""
from __future__ import annotations

import argparse
import json
import logging
import os

from . import settings
from .govt_opendata import GovtScraper, parse_record
from .job104 import Job104Scraper, parse_detail
from .lake import LakeWriter

log = logging.getLogger("ingest")


def _offline_postings(source: str):
    path = os.path.join(settings.SAMPLE_DATA_DIR, f"{source}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Sample file {path} not found. Run with --live or add sample data."
        )
    with open(path, encoding="utf-8") as f:
        records = json.load(f)
    log.info("Offline: replaying %d sample records from %s", len(records), path)
    for rec in records:
        if source == "govt":
            yield parse_record(rec)
        elif source == "job104":
            yield parse_detail(rec.get("jobId") or rec.get("data", {}).get("jobId"), rec)


def _live_postings(source: str, max_records: int | None):
    if source == "govt":
        scraper = GovtScraper(max_records=max_records)
    elif source == "job104":
        scraper = Job104Scraper(max_records=max_records)
    else:
        raise ValueError(source)
    with scraper:
        yield from scraper.fetch()


def main():
    ap = argparse.ArgumentParser(description="Land job postings into the data lake.")
    ap.add_argument("--source", required=True, choices=["govt", "job104"])
    ap.add_argument("--live", action="store_true", help="scrape live (default: offline sample)")
    ap.add_argument("--max", type=int, default=None, help="max records (live only)")
    args = ap.parse_args()

    postings = (
        _live_postings(args.source, args.max) if args.live else _offline_postings(args.source)
    )

    writer = LakeWriter()
    try:
        n = writer.write_many(postings)
    finally:
        writer.close()
    log.info("DONE: ingested %d %s postings into the lake.", n, args.source)


if __name__ == "__main__":
    main()
