"""Pydantic response models (the API contract = the monetizable data feed)."""
from __future__ import annotations

from pydantic import BaseModel


class SkillOverview(BaseModel):
    skill: str
    category: str | None = None
    total_postings: int
    latest_month: str | None = None
    latest_count: int | None = None
    prev_count: int | None = None
    mom_pct: float | None = None


class SalaryBenchmark(BaseModel):
    skill: str
    region: str
    seniority: str
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None
    sample_size: int


class TrendPoint(BaseModel):
    year_month: str
    postings: int


class SkillTrend(BaseModel):
    skill: str
    points: list[TrendPoint]


class Kpi(BaseModel):
    metric: str
    value: float
