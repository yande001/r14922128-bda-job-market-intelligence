"""Stage 4 — skill_extract: gazetteer match -> long posting x skill table.

The core value-add. Explainable dictionary matching (scrapers/config/skills.yaml);
skillNer/MLlib is documented as the future upgrade.
"""
from __future__ import annotations

from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, StringType

from common import (
    get_spark,
    load_skill_patterns,
    read_silver,
    skill_category_map,
    write_silver,
)


def run(spark):
    df = read_silver(spark, "postings_norm")

    patterns = load_skill_patterns()
    bc = spark.sparkContext.broadcast(patterns)

    @F.udf(returnType=ArrayType(StringType()))
    def extract_skills(text):
        if not text:
            return []
        return [canon for canon, _cat, pat in bc.value if pat.search(text)]

    with_skills = df.withColumn("skills", extract_skills(F.col("full_text")))

    exploded = (
        with_skills.withColumn("skill", F.explode("skills"))
        .select(
            "source", "job_id", "skill", "year_month", "region", "seniority",
            "salary_monthly_mid", "company", "title",
        )
    )

    # attach category via a small dim
    cat_rows = [(k, v) for k, v in skill_category_map().items()]
    dim = spark.createDataFrame(cat_rows, ["skill", "category"])
    exploded = exploded.join(F.broadcast(dim), on="skill", how="left")

    write_silver(exploded, "posting_skills")
    n = exploded.count()
    print(f"[skill_extract] {n} posting-skill rows across {exploded.select('skill').distinct().count()} skills")
    return n


if __name__ == "__main__":
    spark = get_spark("skill_extract")
    run(spark)
    spark.stop()
