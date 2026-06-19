"""Shared Spark helpers: session (MinIO s3a + Postgres JDBC), lake paths, gazetteer."""
from __future__ import annotations

import os
import re

import yaml
from pyspark.sql import DataFrame, SparkSession

# --- config from env (set by docker-compose) -------------------------------
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "jobmarket")

PG_HOST = os.environ.get("POSTGRES_HOST", "postgres")
PG_PORT = os.environ.get("POSTGRES_PORT", "5432")
PG_DB = os.environ.get("POSTGRES_DB", "jobmarket")
PG_USER = os.environ.get("POSTGRES_USER", "jobmarket")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "jobmarket")

SKILLS_YAML = os.environ.get("SKILLS_YAML", "/opt/app/scrapers/config/skills.yaml")

_BUCKET = f"s3a://{MINIO_BUCKET}"
BRONZE_GLOB = f"{_BUCKET}/bronze/*/*.json"


def silver_path(name: str) -> str:
    return f"{_BUCKET}/silver/{name}"


def get_spark(app_name: str = "jobmarket") -> SparkSession:
    endpoint_host = re.sub(r"^https?://", "", MINIO_ENDPOINT)
    return (
        SparkSession.builder.appName(app_name)
        .config("spark.hadoop.fs.s3a.endpoint", endpoint_host)
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .config(
            "spark.hadoop.fs.s3a.aws.credentials.provider",
            "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
        )
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.sql.session.timeZone", "Asia/Taipei")
        .config("spark.sql.shuffle.partitions", "8")  # small data: avoid file explosion
        .getOrCreate()
    )


def read_silver(spark: SparkSession, name: str) -> DataFrame:
    return spark.read.parquet(silver_path(name))


def write_silver(df: DataFrame, name: str) -> None:
    # small dataset: coalesce to a handful of files to avoid the small-file problem
    df.coalesce(4).write.mode("overwrite").parquet(silver_path(name))


def write_postgres(df: DataFrame, table: str) -> None:
    """Write a gold mart to Postgres, truncating (not dropping) to keep schema+indexes."""
    (
        df.write.format("jdbc")
        .option("url", f"jdbc:postgresql://{PG_HOST}:{PG_PORT}/{PG_DB}")
        .option("dbtable", table)
        .option("user", PG_USER)
        .option("password", PG_PASSWORD)
        .option("driver", "org.postgresql.Driver")
        .option("truncate", "true")
        .mode("overwrite")
        .save()
    )


# --- skill gazetteer -------------------------------------------------------
def load_skill_patterns() -> list[tuple[str, str, "re.Pattern"]]:
    """Return [(canonical_skill, category, compiled_regex), ...] from skills.yaml.

    ASCII aliases get word boundaries; CJK aliases match as substrings.
    """
    with open(SKILLS_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    patterns: list[tuple[str, str, re.Pattern]] = []
    for category, skills in data.items():
        for canonical, aliases in skills.items():
            alts = []
            for alias in aliases:
                a = alias.strip().lower()
                if not a:
                    continue
                esc = re.escape(a)
                if re.fullmatch(r"[a-z0-9 .+#/]+", a):
                    alts.append(rf"(?<![a-z0-9]){esc}(?![a-z0-9])")
                else:
                    alts.append(esc)
            if alts:
                patterns.append((canonical, category, re.compile("|".join(alts))))
    return patterns


def skill_category_map() -> dict[str, str]:
    with open(SKILLS_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {canon: cat for cat, skills in data.items() for canon in skills}
