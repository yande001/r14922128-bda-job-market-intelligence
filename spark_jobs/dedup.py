"""Stage 2 — dedup: collapse the same posting seen across sources/days.

Key = normalized (company, title, region). Keeps the most recent record and
records first_seen / last_seen / times_seen for honest demand counting.
"""
from __future__ import annotations

from pyspark.sql import Window
from pyspark.sql import functions as F

from common import get_spark, read_silver, write_silver


def run(spark):
    df = read_silver(spark, "postings_clean")

    key = [
        F.lower(F.trim(F.coalesce(F.col("company"), F.lit("")))),
        F.lower(F.trim(F.coalesce(F.col("title"), F.lit("")))),
        F.col("region"),
    ]
    w = Window.partitionBy(*key).orderBy(
        F.col("posted_date").desc_nulls_last(), F.col("fetched_at").desc_nulls_last()
    )
    wagg = Window.partitionBy(*key)

    out = (
        df.withColumn("_rn", F.row_number().over(w))
        .withColumn("first_seen", F.min("posted_date").over(wagg))
        .withColumn("last_seen", F.max("posted_date").over(wagg))
        .withColumn("times_seen", F.count(F.lit(1)).over(wagg))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )

    write_silver(out, "postings_dedup")
    before, after = df.count(), out.count()
    print(f"[dedup] {before} -> {after} postings ({before - after} duplicates removed)")
    return after


if __name__ == "__main__":
    spark = get_spark("dedup")
    run(spark)
    spark.stop()
