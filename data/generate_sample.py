"""Generate realistic, PII-free SAMPLE data so the pipeline runs fully offline.

Output (raw source formats, replayed through the real parsers):
  * data/sample_data/govt.json    — govt open-data records (Chinese-suffixed keys)
  * data/sample_data/job104.json  — 104 detail payloads

This is synthetic-but-plausible data for demo/grading only; the live scrapers
(scrapers/govt_opendata.py, scrapers/job104.py) pull the real thing with --live.
Deterministic (seeded) so re-running reproduces identical files.
"""
from __future__ import annotations

import json
import os
import random

random.seed(20260619)

OUT_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
os.makedirs(OUT_DIR, exist_ok=True)

# role -> (core skills, optional skills, monthly salary base by seniority)
ROLES = {
    "後端工程師 Backend Engineer": {
        "core": ["Python", "Java", "PostgreSQL", "REST API"],
        "opt": ["Go", "Docker", "Kubernetes", "AWS", "Redis", "MySQL", "Spring Boot"],
        "base": {"junior": 48000, "mid": 70000, "senior": 100000},
    },
    "前端工程師 Frontend Engineer": {
        "core": ["JavaScript", "TypeScript", "React", "CSS"],
        "opt": ["Vue", "Next.js", "HTML", "Node.js", "GraphQL"],
        "base": {"junior": 45000, "mid": 65000, "senior": 92000},
    },
    "資料工程師 Data Engineer": {
        "core": ["Python", "Spark", "SQL", "ETL"],
        "opt": ["Hadoop", "Kafka", "Airflow", "AWS", "Snowflake", "BigQuery", "Docker"],
        "base": {"junior": 55000, "mid": 82000, "senior": 120000},
    },
    "資料科學家 Data Scientist": {
        "core": ["Python", "Machine Learning", "Statistics", "SQL"],
        "opt": ["PyTorch", "TensorFlow", "NLP", "Deep Learning", "LLM", "scikit-learn"],
        "base": {"junior": 60000, "mid": 90000, "senior": 130000},
    },
    "DevOps工程師 DevOps Engineer": {
        "core": ["Docker", "Kubernetes", "Linux", "CI/CD"],
        "opt": ["Terraform", "AWS", "GCP", "Ansible", "Prometheus", "Grafana"],
        "base": {"junior": 58000, "mid": 85000, "senior": 120000},
    },
    "全端工程師 Fullstack Engineer": {
        "core": ["JavaScript", "React", "Node.js", "MongoDB"],
        "opt": ["TypeScript", "Python", "Docker", "PostgreSQL", "AWS"],
        "base": {"junior": 50000, "mid": 72000, "senior": 100000},
    },
    "行動開發工程師 Mobile Engineer": {
        "core": ["Swift", "Kotlin"],
        "opt": ["React Native", "Flutter", "iOS", "Android", "Java"],
        "base": {"junior": 50000, "mid": 74000, "senior": 102000},
    },
}

CITIES = ["台北市", "台北市", "新北市", "新竹市", "台中市", "高雄市", "遠端"]
SENIORITY = ["junior", "mid", "senior"]
EXP_BY_SEN = {"junior": "1年以下", "mid": "2年以上", "senior": "5年以上"}
EDU_BY_SEN = {"junior": "專科", "mid": "大學", "senior": "碩士"}
MONTHS = ["01", "02", "03", "04", "05", "06"]

# Skills whose demand GROWS over the half-year (extra weight in later months) —
# gives the trend charts a real signal to show.
TRENDING = {"LLM": 0.5, "Kubernetes": 0.4, "Kafka": 0.35, "Spark": 0.3, "Go": 0.25}


def pick_skills(role: dict, month_idx: int) -> list[str]:
    skills = list(role["core"])
    for s in role["opt"]:
        p = 0.45
        if s in TRENDING:
            p += TRENDING[s] * (month_idx / (len(MONTHS) - 1))
        if random.random() < p:
            skills.append(s)
    return sorted(set(skills))


def salary_for(role: dict, sen: str, skills: list[str]) -> tuple[int, int]:
    base = role["base"][sen]
    premium = sum(3000 for s in skills if s in TRENDING)  # hot skills pay more
    lo = base + premium + random.randint(-3000, 3000)
    hi = int(lo * random.uniform(1.15, 1.45))
    return (round(lo, -3), round(hi, -3))


def make_records(n_govt: int = 260, n_104: int = 150):
    govt, j104 = [], []
    role_names = list(ROLES)

    for i in range(n_govt):
        name = random.choice(role_names)
        role = ROLES[name]
        sen = random.choices(SENIORITY, weights=[3, 4, 2])[0]
        mi = random.randint(0, len(MONTHS) - 1)
        skills = pick_skills(role, mi)
        lo, hi = salary_for(role, sen, skills)
        skill_text = "、".join(skills)
        hire_id = 14000000 + i
        govt.append({
            "OCCU_DESC（職務名稱）": name,
            "WK_TYPE（職務性質）": "全職",
            "CJOB1_COUNT（職務大類別代碼）": "23",
            "CJOB_NAME1（職務大類別名稱）": "資訊／軟體／系統",
            "CJOB2_COUNT（職務小類別代碼）": "230101",
            "CJOB_NAME2（職務小類別名稱）": "軟體工程師",
            "JOB_PERSON（雇用人數）": str(random.randint(1, 5)),
            "STOP_DATE（應徵截止日期）": f"2026{MONTHS[mi]}28",
            "JOB_DETAIL（工作內容）": (
                f"負責產品開發與維護。需求技能：{skill_text}。"
                f"與跨部門團隊協作，具備良好溝通能力。"
            ),
            "CITYNAME（工作地點）": random.choice(CITIES) + "信義區",
            "EXPERIENCE（工作經驗）": EXP_BY_SEN[sen],
            "WKTIME（工作時間）": "日班",
            "SALARYCD（核薪方式）": "月薪",
            "NT_L（薪資範圍下限）": str(lo),
            "NT_U（薪資範圍上限）": str(hi),
            "EDGRDESC（最低學歷要求）": EDU_BY_SEN[sen],
            "URL_QUERY（職缺資料URL）": (
                f"https://job.taiwanjobs.gov.tw/Internet/jobwanted/JobDetail.aspx?"
                f"EMPLOYER_ID={2000000 + i}&HIRE_ID={hire_id}"
            ),
            "COMPNAME（公司名稱）": f"範例科技股份有限公司 {i % 40}",
            "TRANDATE（職缺更新日期）": f"2026{MONTHS[mi]}{random.randint(10, 25):02d}",
        })

    for i in range(n_104):
        name = random.choice(role_names)
        role = ROLES[name]
        sen = random.choices(SENIORITY, weights=[3, 4, 2])[0]
        mi = random.randint(0, len(MONTHS) - 1)
        skills = pick_skills(role, mi)
        lo, hi = salary_for(role, sen, skills)
        jid = f"7{i:06d}"
        j104.append({
            "jobId": jid,
            "data": {
                "header": {
                    "jobName": name,
                    "custName": f"104範例企業 {i % 35}",
                    "appearDate": f"2026{MONTHS[mi]}{random.randint(1, 20):02d}",
                },
                "jobDetail": {
                    "jobDescription": (
                        f"我們正在尋找{name}，參與大型系統開發。"
                        f"技術棧涵蓋 {', '.join(skills)}。"
                    ),
                    "salary": f"月薪{lo:,}~{hi:,}元",
                    "salaryMin": lo,
                    "salaryMax": hi,
                    "addressRegion": random.choice(CITIES),
                    "needEmp": str(random.randint(1, 3)),
                    "jobCategory": [{"description": "軟體工程師"}],
                },
                "condition": {
                    "workExp": EXP_BY_SEN[sen],
                    "edu": EDU_BY_SEN[sen],
                    "major": "資訊相關科系",
                    "skill": [{"description": s} for s in skills],
                    "specialty": [{"description": s} for s in skills if s in TRENDING],
                    "other": f"熟悉 {', '.join(skills)} 尤佳。",
                    "language": "英文 中等",
                },
            },
        })

    return govt, j104


def main():
    govt, j104 = make_records()
    with open(os.path.join(OUT_DIR, "govt.json"), "w", encoding="utf-8") as f:
        json.dump(govt, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT_DIR, "job104.json"), "w", encoding="utf-8") as f:
        json.dump(j104, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(govt)} govt + {len(j104)} job104 sample records to {OUT_DIR}")


if __name__ == "__main__":
    main()
