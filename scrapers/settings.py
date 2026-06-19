"""Environment-driven settings shared by ingestion code."""
import os


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


# MinIO / S3 (data lake). Inside containers the host is "minio"; from the host
# machine it is "localhost". docker-compose sets MINIO_ENDPOINT per service.
MINIO_ENDPOINT = _get("MINIO_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY = _get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = _get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = _get("MINIO_BUCKET", "jobmarket")

# MongoDB (raw store)
MONGO_URI = _get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = _get("MONGO_DB", "jobmarket")
MONGO_COLLECTION = _get("MONGO_COLLECTION", "raw_postings")

# Scraper politeness (data ethics)
SCRAPE_DELAY_SECONDS = float(_get("SCRAPE_DELAY_SECONDS", "2.5"))
SCRAPE_MAX_RECORDS = int(_get("SCRAPE_MAX_RECORDS", "1500"))
SCRAPE_USER_AGENT = _get(
    "SCRAPE_USER_AGENT",
    "BDA-FinalProject-Academic/1.0 (NTU coursework; contact r14922128@csie.ntu.edu.tw)",
)

# Where committed offline sample data lives (relative to repo root).
SAMPLE_DATA_DIR = _get("SAMPLE_DATA_DIR", "data/sample_data")
