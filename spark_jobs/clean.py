"""Stage 1 — clean: bronze JSON (MinIO) -> typed, normalized silver Parquet."""
from __future__ import annotations

from pyspark.sql import functions as F

from common import BRONZE_GLOB, get_spark, write_silver

EXPECTED_COLS = [
    "source", "job_id", "title", "company", "description", "requirements",
    "salary_text", "salary_min", "salary_max", "salary_type", "city",
    "headcount", "education", "experience", "category", "url",
    "posted_date", "fetched_at",
]


def run(spark):
    df = spark.read.option("multiLine", "true").json(BRONZE_GLOB)
    for c in EXPECTED_COLS:
        if c not in df.columns:
            df = df.withColumn(c, F.lit(None))
    df = df.select(*EXPECTED_COLS)

    # year_month from posted_date (fallback to fetched_at)
    ym = F.coalesce(
        F.substring(F.col("posted_date"), 1, 7),
        F.substring(F.col("fetched_at"), 1, 7),
    )

    # seniority from free-text experience
    exp = F.coalesce(F.col("experience"), F.lit(""))
    seniority = (
        F.when(exp.rlike("5年|資深|senior|10年|7年"), F.lit("senior"))
        .when(exp.rlike("2年|3年|4年|mid"), F.lit("mid"))
        .otherwise(F.lit("junior"))
    )

    # region: leading city token, or 遠端 (remote)
    region = F.regexp_extract(F.coalesce(F.col("city"), F.lit("")), r"(遠端|.{2,3}?[市縣])", 1)
    region = F.when(region == "", F.lit("其他")).otherwise(region)

    full_text = F.lower(
        F.concat_ws(
            " ",
            F.coalesce(F.col("title"), F.lit("")),
            F.coalesce(F.col("description"), F.lit("")),
            F.coalesce(F.col("requirements"), F.lit("")),
        )
    )

    out = (
        df.withColumn("year_month", ym)
        .withColumn("seniority", seniority)
        .withColumn("region", region)
        .withColumn("full_text", full_text)
        .withColumn("salary_min", F.col("salary_min").cast("double"))
        .withColumn("salary_max", F.col("salary_max").cast("double"))
        .withColumn("headcount", F.col("headcount").cast("int"))
        .filter(F.col("job_id").isNotNull() & F.col("title").isNotNull())
    )

    write_silver(out, "postings_clean")
    n = out.count()
    print(f"[clean] wrote {n} cleaned postings")
    return n


if __name__ == "__main__":
    spark = get_spark("clean")
    run(spark)
    spark.stop()
