"""Run the full batch pipeline in one Spark session: bronze -> silver -> gold."""
from __future__ import annotations

import os
import sys

# allow `import clean` etc. when launched via spark-submit run_all.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import clean
import dedup
import salary_norm
import skill_extract
import trend_aggregate
from common import get_spark


def main():
    spark = get_spark("jobmarket-pipeline")
    spark.sparkContext.setLogLevel("WARN")
    print("=== Job-Market Intelligence batch pipeline ===")
    clean.run(spark)
    dedup.run(spark)
    salary_norm.run(spark)
    skill_extract.run(spark)
    trend_aggregate.run(spark)
    print("=== pipeline complete ===")
    spark.stop()


if __name__ == "__main__":
    main()
