"""Stage 3 — salary_norm: normalize pay to monthly TWD.

month -> as-is, year -> /12, hour -> x176 (22d x 8h), day -> x22.
Negotiable / missing -> null. Implausible values are dropped.
"""
from __future__ import annotations

from pyspark.sql import functions as F

from common import get_spark, read_silver, write_silver

HOURS_PER_MONTH = 176
DAYS_PER_MONTH = 22


def _to_monthly(col):
    st = F.col("salary_type")
    return (
        F.when(st == "month", col)
        .when(st == "year", col / 12.0)
        .when(st == "hour", col * HOURS_PER_MONTH)
        .when(st == "day", col * DAYS_PER_MONTH)
        .otherwise(F.lit(None))
    )


def run(spark):
    df = read_silver(spark, "postings_dedup")

    m_min = _to_monthly(F.col("salary_min"))
    m_max = _to_monthly(F.col("salary_max"))

    out = (
        df.withColumn("salary_monthly_min", m_min)
        .withColumn("salary_monthly_max", m_max)
        .withColumn(
            "salary_monthly_mid",
            F.when(
                m_min.isNotNull() & m_max.isNotNull(), (m_min + m_max) / 2.0
            ).otherwise(F.coalesce(m_min, m_max)),
        )
    )
    # drop implausible (keep 10k–1M monthly band); null salaries are kept as null
    out = out.withColumn(
        "salary_monthly_mid",
        F.when(
            (F.col("salary_monthly_mid") >= 10000) & (F.col("salary_monthly_mid") <= 1000000),
            F.col("salary_monthly_mid"),
        ).otherwise(F.lit(None)),
    )

    write_silver(out, "postings_norm")
    n_sal = out.filter(F.col("salary_monthly_mid").isNotNull()).count()
    print(f"[salary_norm] {out.count()} postings, {n_sal} with usable monthly salary")
    return n_sal


if __name__ == "__main__":
    spark = get_spark("salary_norm")
    run(spark)
    spark.stop()
