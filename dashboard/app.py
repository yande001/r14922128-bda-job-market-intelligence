"""Job-Market Intelligence dashboard (human-facing demo over the API)."""
from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Job-Market Intelligence", page_icon="📊", layout="wide")


@st.cache_data(ttl=60)
def get(path: str, params: dict | None = None):
    r = requests.get(f"{API}{path}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


st.title("📊 Taiwan Tech Job-Market Intelligence")
st.caption("Real-time, skill-level demand & salary benchmarks — powered by a Spark pipeline.")

# --- KPIs ---
try:
    kpis = {k["metric"]: k["value"] for k in get("/summary")}
except Exception as e:  # noqa: BLE001
    st.error(f"Cannot reach API at {API}. Has the pipeline run? ({e})")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Postings analyzed", f"{int(kpis.get('total_postings', 0)):,}")
c2.metric("Skills tracked", int(kpis.get("distinct_skills", 0)))
c3.metric("Companies", int(kpis.get("distinct_companies", 0)))
c4.metric("Median salary (monthly)", f"NT${int(kpis.get('median_monthly_salary', 0)):,}")

st.divider()
left, right = st.columns(2)

# --- View 1: trending skills (MoM growth) ---
with left:
    st.subheader("🔥 Trending skills (MoM demand growth)")
    trending = pd.DataFrame(get("/skills/trending", {"limit": 10, "min_postings": 5}))
    if not trending.empty:
        fig = px.bar(
            trending.sort_values("mom_pct"),
            x="mom_pct", y="skill", orientation="h",
            labels={"mom_pct": "Month-over-month growth (%)", "skill": ""},
            color="mom_pct", color_continuous_scale="Tealgrn",
        )
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No trend data yet.")

# --- View 2: most in-demand skills ---
with right:
    st.subheader("📈 Most in-demand skills (total postings)")
    overview = pd.DataFrame(get("/skills", {"limit": 15}))
    if not overview.empty:
        fig = px.bar(
            overview.sort_values("total_postings"),
            x="total_postings", y="skill", orientation="h",
            labels={"total_postings": "Postings", "skill": ""},
            color="category",
        )
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- View 3: salary benchmark + per-skill demand trend ---
sk_left, sk_right = st.columns(2)
skill_list = sorted(overview["skill"].tolist()) if not overview.empty else []

with sk_left:
    st.subheader("💰 Salary benchmark by skill")
    region = st.selectbox("Region", ["ALL", "台北市", "新北市", "新竹市", "台中市", "高雄市", "遠端"])
    seniority = st.selectbox("Seniority", ["ALL", "junior", "mid", "senior"])
    bench = pd.DataFrame(get("/salary", {"region": region, "seniority": seniority, "limit": 15}))
    if not bench.empty:
        bench = bench.sort_values("p50", ascending=False)
        fig = px.bar(
            bench, x="skill", y=["p25", "p50", "p75"],
            barmode="group", labels={"value": "Monthly salary (NT$)", "variable": "Percentile"},
        )
        fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), xaxis_tickangle=-40)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No salary data for this filter.")

with sk_right:
    st.subheader("🕒 Skill demand over time")
    if skill_list:
        skill = st.selectbox("Skill", skill_list, index=min(0, len(skill_list) - 1))
        trend = get(f"/skills/{skill}/trend")
        tdf = pd.DataFrame(trend["points"])
        if not tdf.empty:
            fig = px.line(tdf, x="year_month", y="postings", markers=True,
                          labels={"year_month": "Month", "postings": "Postings"})
            fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig, use_container_width=True)

st.caption("Data: 台灣就業通 (gov open data) + 104.com.tw enrichment · aggregates only, no PII.")
