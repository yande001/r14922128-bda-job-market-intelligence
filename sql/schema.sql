-- Gold marts served by the API. Created at first Postgres start.
-- The Spark loader writes with mode=overwrite + truncate=true, so it preserves
-- these table definitions and indexes across pipeline reruns.

CREATE TABLE IF NOT EXISTS skill_demand_monthly (
    skill       TEXT   NOT NULL,
    year_month  TEXT   NOT NULL,
    postings    BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_demand_skill ON skill_demand_monthly (skill);
CREATE INDEX IF NOT EXISTS idx_demand_month ON skill_demand_monthly (year_month);

CREATE TABLE IF NOT EXISTS skill_overview (
    skill           TEXT   NOT NULL,
    category        TEXT,
    total_postings  BIGINT NOT NULL,
    latest_month    TEXT,
    latest_count    BIGINT,
    prev_count      BIGINT,
    mom_pct         DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS idx_overview_skill ON skill_overview (skill);
CREATE INDEX IF NOT EXISTS idx_overview_total ON skill_overview (total_postings DESC);

CREATE TABLE IF NOT EXISTS skill_salary_benchmark (
    skill        TEXT   NOT NULL,
    region       TEXT   NOT NULL,
    seniority    TEXT   NOT NULL,
    p25          DOUBLE PRECISION,
    p50          DOUBLE PRECISION,
    p75          DOUBLE PRECISION,
    sample_size  BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_salary_skill ON skill_salary_benchmark (skill);
CREATE INDEX IF NOT EXISTS idx_salary_filter ON skill_salary_benchmark (skill, region, seniority);

CREATE TABLE IF NOT EXISTS market_kpi (
    metric  TEXT NOT NULL,
    value   DOUBLE PRECISION
);
