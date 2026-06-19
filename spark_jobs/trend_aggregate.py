"""Stage 5 — trend_aggregate: build gold marts and load them into PostgreSQL.

Marts (consumed by the API):
  * skill_demand_monthly   (skill, year_month, postings)
  * skill_overview         (skill, category, total_postings, latest_month,
                            latest_count, prev_count, mom_pct)
  * skill_salary_benchmark (skill, region, seniority, p25, p50, p75, sample_size)
  * market_kpi             (metric, value)
"""
from __future__ import annotations

from pyspark.sql import Window
from pyspark.sql import functions as F

from common import get_spark, read_silver, write_postgres

PCTS = [0.25, 0.5, 0.75]


def _salary_agg(df, group_cols):
    return (
        df.groupBy(*group_cols)
        .agg(
            F.percentile_approx("salary_monthly_mid", PCTS, 1000).alias("p"),
            F.count(F.lit(1)).alias("sample_size"),
        )
        .withColumn("p25", F.round(F.col("p")[0]).cast("double"))
        .withColumn("p50", F.round(F.col("p")[1]).cast("double"))
        .withColumn("p75", F.round(F.col("p")[2]).cast("double"))
        .drop("p")
    )


def run(spark):
    skills = read_silver(spark, "posting_skills").withColumn(
        "uid", F.concat_ws("-", F.col("source"), F.col("job_id"))
    )
    postings = read_silver(spark, "postings_norm").withColumn(
        "uid", F.concat_ws("-", F.col("source"), F.col("job_id"))
    )

    # --- skill_demand_monthly ---
    monthly = (
        skills.filter(F.col("year_month").isNotNull())
        .groupBy("skill", "year_month")
        .agg(F.countDistinct("uid").alias("postings"))
    )
    write_postgres(monthly.select("skill", "year_month", "postings"), "skill_demand_monthly")

    # --- skill_overview (with month-over-month change) ---
    w_time = Window.partitionBy("skill").orderBy("year_month")
    w_rank = Window.partitionBy("skill").orderBy(F.col("year_month").desc())
    ranked = (
        monthly.withColumn("prev_count", F.lag("postings").over(w_time))
        .withColumn("rn", F.row_number().over(w_rank))
        .filter(F.col("rn") == 1)
    )
    totals = skills.groupBy("skill").agg(
        F.countDistinct("uid").alias("total_postings"),
        F.first("category", ignorenulls=True).alias("category"),
    )
    overview = (
        totals.join(ranked, on="skill", how="left")
        .withColumn(
            "mom_pct",
            F.when(
                (F.col("prev_count").isNotNull()) & (F.col("prev_count") > 0),
                F.round((F.col("postings") - F.col("prev_count")) / F.col("prev_count") * 100, 1),
            ).otherwise(F.lit(None)).cast("double"),
        )
        .select(
            "skill", "category", "total_postings",
            F.col("year_month").alias("latest_month"),
            F.col("postings").alias("latest_count"),
            "prev_count", "mom_pct",
        )
    )
    write_postgres(overview, "skill_overview")

    # --- skill_salary_benchmark (3 grains, unioned) ---
    sal = skills.filter(F.col("salary_monthly_mid").isNotNull())
    g_all = _salary_agg(sal, ["skill"]).withColumn("region", F.lit("ALL")).withColumn("seniority", F.lit("ALL"))
    g_reg = _salary_agg(sal, ["skill", "region"]).withColumn("seniority", F.lit("ALL"))
    g_sen = _salary_agg(sal, ["skill", "seniority"]).withColumn("region", F.lit("ALL"))
    cols = ["skill", "region", "seniority", "p25", "p50", "p75", "sample_size"]
    bench = g_all.select(*cols).unionByName(g_reg.select(*cols)).unionByName(g_sen.select(*cols))
    bench = bench.filter(F.col("sample_size") >= 3)
    write_postgres(bench, "skill_salary_benchmark")

    # --- market_kpi ---
    total_postings = postings.count()
    distinct_skills = skills.select("skill").distinct().count()
    distinct_companies = postings.select("company").distinct().count()
    median_salary = (
        postings.filter(F.col("salary_monthly_mid").isNotNull())
        .agg(F.percentile_approx("salary_monthly_mid", 0.5, 1000).alias("m"))
        .collect()[0]["m"]
    )
    kpi = spark.createDataFrame(
        [
            ("total_postings", float(total_postings)),
            ("distinct_skills", float(distinct_skills)),
            ("distinct_companies", float(distinct_companies)),
            ("median_monthly_salary", float(median_salary or 0)),
        ],
        ["metric", "value"],
    )
    write_postgres(kpi, "market_kpi")

    print(
        f"[trend_aggregate] gold marts loaded: {total_postings} postings, "
        f"{distinct_skills} skills, {distinct_companies} companies, "
        f"median salary {median_salary}"
    )


if __name__ == "__main__":
    spark = get_spark("trend_aggregate")
    run(spark)
    spark.stop()
