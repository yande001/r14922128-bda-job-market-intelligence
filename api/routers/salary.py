"""Salary benchmark endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ..db import query
from ..schemas import SalaryBenchmark

router = APIRouter(prefix="/salary", tags=["salary"])


@router.get("", response_model=list[SalaryBenchmark])
def salary_benchmark(
    skill: str | None = None,
    region: str = Query("ALL", description="city like 台北市, or ALL"),
    seniority: str = Query("ALL", description="junior | mid | senior | ALL"),
    limit: int = Query(100, ge=1, le=500),
):
    sql = "SELECT * FROM skill_salary_benchmark WHERE region = %s AND seniority = %s"
    params: list = [region, seniority]
    if skill:
        sql += " AND skill = %s"
        params.append(skill)
    sql += " ORDER BY p50 DESC NULLS LAST LIMIT %s"
    params.append(limit)
    return query(sql, tuple(params))
