"""Skill demand endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..db import query
from ..schemas import SkillOverview, SkillTrend, TrendPoint

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillOverview])
def list_skills(
    limit: int = Query(100, ge=1, le=500),
    category: str | None = None,
):
    sql = "SELECT * FROM skill_overview"
    params: list = []
    if category:
        sql += " WHERE category = %s"
        params.append(category)
    sql += " ORDER BY total_postings DESC LIMIT %s"
    params.append(limit)
    return query(sql, tuple(params))


@router.get("/trending", response_model=list[SkillOverview])
def trending_skills(limit: int = Query(10, ge=1, le=100), min_postings: int = 5):
    """Skills with the largest month-over-month demand growth."""
    return query(
        """
        SELECT * FROM skill_overview
        WHERE mom_pct IS NOT NULL AND total_postings >= %s
        ORDER BY mom_pct DESC
        LIMIT %s
        """,
        (min_postings, limit),
    )


@router.get("/{skill}/trend", response_model=SkillTrend)
def skill_trend(skill: str):
    rows = query(
        "SELECT year_month, postings FROM skill_demand_monthly "
        "WHERE skill = %s ORDER BY year_month",
        (skill,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"No demand data for skill '{skill}'")
    return SkillTrend(skill=skill, points=[TrendPoint(**r) for r in rows])
