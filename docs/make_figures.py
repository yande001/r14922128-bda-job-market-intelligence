"""Generate the architecture diagram + report figures (from the LIVE API).

Run after `make demo` while the API is up:  python3 docs/make_figures.py
Outputs PNGs into docs/figures/.
"""
from __future__ import annotations

import json
import os
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, patches

# --- CJK font so Chinese skill/city names render ---
for cand in ["Noto Sans CJK TC", "Noto Sans CJK SC", "Noto Sans CJK JP"]:
    try:
        font_manager.findfont(cand, fallback_to_default=False)
        plt.rcParams["font.sans-serif"] = [cand]
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

API = os.environ.get("API_BASE_URL", "http://localhost:8000")
OUT = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(OUT, exist_ok=True)

TEAL = "#0f766e"
GREY = "#334155"


def api(path, params=""):
    url = f"{API}{path}{params}"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.load(r)


# figures are capped to this physical width (inches) so LibreOffice places them
# full-width without clipping (A4 text width ~6.7in).
FIGW = 6.4


# ---------------------------------------------------------------- architecture
def architecture():
    """Compact 2x3 'snake' so it stays readable at page width."""
    fig, ax = plt.subplots(figsize=(FIGW, 3.7))
    ax.axis("off")
    # (label, body, color, col, row)  row 0 = top
    stages = [
        ("1. Ingestion", "Python scrapers\n(govt API + 104)", "#1e88e5", 0, 0),
        ("2. Data Lake", "MinIO (S3)\nbronze/silver/gold", "#8e24aa", 1, 0),
        ("3. Raw Store", "MongoDB\n(schema-on-read)", "#43a047", 2, 0),
        ("4. Batch", "PySpark\nclean→skill→salary", "#fb8c00", 2, 1),
        ("5. Serving", "PostgreSQL\ngold marts", "#3949ab", 1, 1),
        ("6. Delivery", "FastAPI + Streamlit\nAPI / dashboard", "#e53935", 0, 1),
    ]
    w, h, gapx, gapy = 2.7, 1.7, 0.7, 1.1
    x0, y0 = 0.3, 2.6

    def cx(col):
        return x0 + col * (w + gapx) + w / 2

    def cy(row):
        return y0 - row * (h + gapy) + h / 2

    for title, body, color, col, row in stages:
        x = x0 + col * (w + gapx)
        y = (y0 - row * (h + gapy))
        ax.add_patch(patches.FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.14",
            linewidth=2, edgecolor=color, facecolor=color + "22"))
        ax.text(x + w / 2, y + h - 0.42, title, ha="center", va="center",
                fontsize=11, fontweight="bold", color=color)
        ax.text(x + w / 2, y + 0.55, body, ha="center", va="center",
                fontsize=8.5, color=GREY)

    def arrow(c1, r1, c2, r2):
        ax.annotate("", xy=(cx(c2), cy(r2)), xytext=(cx(c1), cy(r1)),
                    arrowprops=dict(arrowstyle="-|>", lw=2, color=GREY,
                                    shrinkA=42, shrinkB=42))
    arrow(0, 0, 1, 0); arrow(1, 0, 2, 0)       # row 0 L->R
    arrow(2, 0, 2, 1)                            # down
    arrow(2, 1, 1, 1); arrow(1, 1, 0, 1)        # row 1 R->L

    ax.text((cx(0) + cx(2)) / 2, y0 + h + 0.25,
            "Job-Market Intelligence — end-to-end data flow",
            ha="center", fontsize=12, fontweight="bold")
    ax.set_xlim(0, x0 + 3 * w + 2 * gapx + 0.3)
    ax.set_ylim(cy(1) - h, y0 + h + 0.7)
    for f in (os.path.join(OUT, "architecture.png"),
              os.path.join(os.path.dirname(__file__), "architecture.png")):
        fig.savefig(f, dpi=90, bbox_inches="tight")
    plt.close(fig)
    print("wrote architecture.png")


def _barh(data, xkey, ykey, title, fname, fmt=None, color=TEAL):
    data = list(reversed(data))
    labels = [d[ykey] for d in data]
    vals = [d[xkey] for d in data]
    fig, ax = plt.subplots(figsize=(FIGW, 4.3))
    bars = ax.barh(labels, vals, color=color)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    if fmt:
        for b, v in zip(bars, vals):
            ax.text(b.get_width(), b.get_y() + b.get_height() / 2, " " + fmt(v),
                    va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname), dpi=90, bbox_inches="tight")
    plt.close(fig)
    print("wrote", fname)


def top_skills():
    data = api("/skills", "?limit=15")
    _barh(data, "total_postings", "skill", "Most in-demand skills (postings)",
          "fig_top_skills.png", fmt=lambda v: str(v))


def trending():
    data = api("/skills/trending", "?limit=10&min_postings=5")
    _barh(data, "mom_pct", "skill", "Trending skills (MoM demand growth %)",
          "fig_trending.png", fmt=lambda v: f"+{v:.0f}%", color="#e53935")


def salary():
    data = api("/salary", "?region=ALL&seniority=ALL&limit=12")
    data = sorted(data, key=lambda d: d["p50"] or 0)
    labels = [d["skill"] for d in data]
    p25 = [d["p25"] for d in data]
    p50 = [d["p50"] for d in data]
    p75 = [d["p75"] for d in data]
    fig, ax = plt.subplots(figsize=(FIGW, 4.6))
    y = range(len(labels))
    ax.hlines(y, p25, p75, color="#94a3b8", lw=4, alpha=0.6)
    ax.scatter(p50, y, color=TEAL, zorder=3, label="median")
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels)
    ax.set_xlabel("Monthly salary (NT$)")
    ax.set_title("Salary benchmark by skill (p25–p75, median)", fontsize=12, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_salary.png"), dpi=90, bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_salary.png")


def trend_lines():
    fig, ax = plt.subplots(figsize=(FIGW, 4.0))
    for skill in ["Spark", "Kubernetes", "LLM", "Go"]:
        try:
            t = api(f"/skills/{skill}/trend")
        except Exception:
            continue
        pts = t["points"]
        ax.plot([p["year_month"] for p in pts], [p["postings"] for p in pts],
                marker="o", label=skill)
    ax.set_title("Skill demand over time", fontsize=12, fontweight="bold")
    ax.set_ylabel("Postings")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_trend_lines.png"), dpi=90, bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_trend_lines.png")


if __name__ == "__main__":
    architecture()
    top_skills()
    trending()
    salary()
    trend_lines()
    print("All figures written to", OUT)
