# Data Ethics, Licensing & PII Policy

This project takes data ethics seriously because (a) the course grades it and (b) a
real version of this product would live or die on it. This document records the
sources we use, what their terms allow, and exactly how we handle personal data.

## Sources and their legal footing

| Source | Access method | License / terms | How we use it |
|---|---|---|---|
| **台灣就業通 / Ministry of Labor** (data.gov.tw #44062) | Official CSV/JSON/API download | **Government Data Open License v1** — free reuse, **commercial use explicitly permitted** | **Primary** source. Legal, reproducible backbone of the pipeline. |
| **104.com.tw** | Undocumented JSON endpoints (`/jobs/search/list`, `/job/ajax/content/{id}`) | No public API license; `robots.txt` returns HTTP 403 to plain clients | **Enrichment only**, low volume, under the academic/research exception. Treated as *tolerated for education*, **not licensed for commercial resale**. |

The asymmetry above is deliberate and is the core of our go-to-market risk
analysis: the *free* source is fully licensed; the *rich* source is not. A
commercial launch would have to (1) license 104 data, (2) negotiate a data
partnership, or (3) rely on the government feed plus first-party survey data.

## Respectful scraping (implemented in `scrapers/base.py`)

- **One request at a time per host** with a configurable minimum delay
  (`SCRAPE_DELAY_SECONDS`, default 2.5s) plus random jitter.
- **Exponential backoff** (tenacity) on 429 / 5xx / transport errors.
- **Honest, identifying User-Agent** naming the project and a contact address.
- **Hard cap** on records per run (`SCRAPE_MAX_RECORDS`, default 1500).
- **Caching**: every raw response is written verbatim to the bronze layer keyed by
  source + id, so re-runs hit the lake, not the website.

## PII handling (Taiwan PDPA)

Taiwan's Personal Data Protection Act (PDPA) treats commercial monetization as a
use *beyond the original collection purpose* (Art. 20), generally requiring
separate consent; Art. 41 attaches criminal penalties to unlawfully profiting from
personal data. There is an academic/statistics public-interest exception that
fits a university project but **not** a commercial product.

Our mitigation — **never store personal data**:

1. The normalized `Posting` schema (`scrapers/base.py`) has **no fields** for
   recruiter name, email, or phone.
2. Free-text fields (`description`, `requirements`) are run through
   `scrub_pii()` which redacts emails and phone numbers before anything is
   persisted.
3. The product sells **aggregates only** — skill counts, salary percentiles,
   trends. No individual record is ever resold.

This means even our raw bronze layer is PII-free by construction, which is the
single most important design decision for a lawful commercial path.

## Reproducibility vs. live scraping

The graded demo runs **fully offline** against a committed, synthetic-but-realistic
sample (`data/sample_data/`, regenerable via `data/generate_sample.py`). Live
collection is opt-in via the `--live` flag and is rate-limited as above. This keeps
the demo deterministic and avoids hammering any third-party site during grading.
