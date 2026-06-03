"""Bellwether chart suite — three standalone charts.

Run:
    python3 docs/make_charts.py

Produces:
    docs/chart_1_subscribers.png   — Subscribers at risk by churn reason
    docs/chart_2_revenue.png       — Revenue at risk by churn reason
    docs/chart_3_trends.png        — Churn reason share over time (trend lines)

Edit the CONFIG block for each chart. No LLM, no Snowflake.
Data loaded from docs/chart_data.json and docs/trend_data.json.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# ─────────────────────────────────────────────────────────────────────────────
# SHARED THEME  (light, minimal — matches reference aesthetic)
# ─────────────────────────────────────────────────────────────────────────────

BG          = "#FFFFFF"
PANEL       = "#FFFFFF"
GRID        = "#EBEBEB"
TEXT        = "#2C2C2C"
TEXT_MUTED  = "#888888"
DPI         = 160
OPEN_AFTER  = True

ARCH_COLORS = {
    "price":       "#4F86C6",
    "efficacy":    "#E07B54",
    "fatigue":     "#6DBF82",
    "life_change": "#A97DC9",
    "involuntary": "#C95F5F",
}
ARCH_LABELS = {
    "price":       "Price",
    "efficacy":    "Efficacy",
    "fatigue":     "Overstock / Fatigue",
    "life_change": "Life Change",
    "involuntary": "Involuntary (Payment)",
}

def _apply_light_theme(ax):
    ax.set_facecolor(PANEL)
    ax.figure.patch.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)

# ─────────────────────────────────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────────────────────────────────

data_path  = Path(__file__).parent / "chart_data.json"
trend_path = Path(__file__).parent / "trend_data.json"

with open(data_path)  as f: data     = json.load(f)
with open(trend_path) as f: raw_trend = json.load(f)

summary = data["summary"]
totals  = data["totals"]

ARCH_ORDER_BAR   = ["price", "life_change", "involuntary", "efficacy", "fatigue"]
ARCH_ORDER_TREND = ["price", "fatigue", "life_change", "involuntary", "efficacy"]

# ─────────────────────────────────────────────────────────────────────────────
# CHART 1 — Subscribers at risk by churn reason
# ─────────────────────────────────────────────────────────────────────────────

C1_TITLE     = "Subscribers at Risk by Churn Reason"
C1_SUBTITLE  = "Active Thesis subscribers · risk tier by P(churn within 30 days)"
C1_YLABEL    = "Subscribers (thousands)"
C1_FOOTNOTE  = "Risk tiers: Low P < 0.10  |  Medium 0.10 to P < 0.50  |  High P >= 0.50"
C1_OUT       = Path(__file__).parent / "chart_1_subscribers.png"
C1_FIG_SIZE  = (9, 5.5)
BAR_W        = 0.55

COLOR_LOW    = "#CCCCDD"
COLOR_MEDIUM = "#F5A623"
COLOR_HIGH   = "#C95F5F"

def chart_1():
    fig, ax = plt.subplots(figsize=C1_FIG_SIZE, facecolor=BG)
    _apply_light_theme(ax)
    ax.yaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)

    x        = np.arange(len(ARCH_ORDER_BAR))
    low_vals = np.array([summary[a]["low"]    for a in ARCH_ORDER_BAR], dtype=float) / 1000
    med_vals = np.array([summary[a]["medium"] for a in ARCH_ORDER_BAR], dtype=float) / 1000
    hi_vals  = np.array([summary[a]["high"]   for a in ARCH_ORDER_BAR], dtype=float) / 1000
    totals_k = low_vals + med_vals + hi_vals

    ax.bar(x, low_vals,              BAR_W, color=COLOR_LOW,    label="Low risk",    zorder=3)
    ax.bar(x, med_vals, BAR_W, bottom=low_vals,              color=COLOR_MEDIUM, label="Medium risk", zorder=3, alpha=0.9)
    ax.bar(x, hi_vals,  BAR_W, bottom=low_vals + med_vals,   color=COLOR_HIGH,   label="High risk",   zorder=3, alpha=0.95)

    for i, (tot, arch) in enumerate(zip(totals_k, ARCH_ORDER_BAR)):
        raw = summary[arch]["total"]
        ax.text(x[i], tot + 0.3, f"{raw:,}", ha="center", va="bottom",
                fontsize=8.5, color=TEXT, fontweight="600")

    ax.set_xticks(x)
    ax.set_xticklabels([ARCH_LABELS[a] for a in ARCH_ORDER_BAR], color=TEXT, fontsize=9)
    ax.set_ylabel(C1_YLABEL, color=TEXT_MUTED, fontsize=9, labelpad=8)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:.0f}"))

    ax.legend(fontsize=8, frameon=False, labelcolor=TEXT, loc="upper right")

    ax.set_title(C1_TITLE,    color=TEXT,       fontsize=13, fontweight="bold", pad=14, loc="left")
    ax.set_xlabel(C1_SUBTITLE, color=TEXT_MUTED, fontsize=8.5, labelpad=10)

    fig.text(0.5, 0.01, C1_FOOTNOTE, ha="center", va="bottom",
             fontsize=7.5, color=TEXT_MUTED, style="italic")

    plt.tight_layout()
    fig.savefig(C1_OUT, dpi=DPI, bbox_inches="tight", facecolor=BG)
    print(f"Saved: {C1_OUT}")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 2 — Revenue at risk by churn reason
# ─────────────────────────────────────────────────────────────────────────────

C2_TITLE    = "Quantifiable Risk to Revenue by Churn Reason"
C2_SUBTITLE = "Monthly estimates  -  USD 79/cycle  -  figures rounded to nearest USD 100"
C2_OUT      = Path(__file__).parent / "chart_2_revenue.png"
C2_FIG_SIZE = (9, 5)

def chart_2():
    fig, ax = plt.subplots(figsize=C2_FIG_SIZE, facecolor=BG)
    _apply_light_theme(ax)
    ax.xaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)

    archs    = ARCH_ORDER_BAR
    x        = np.arange(len(archs))
    rev_vals = np.array([summary[a]["revenue_at_risk"] for a in archs], dtype=float)
    colors   = [ARCH_COLORS[a] for a in archs]
    max_rev  = rev_vals.max()

    bars = ax.barh(x, rev_vals, BAR_W, color=colors, alpha=0.88, zorder=3)

    for i, (val, bar) in enumerate(zip(rev_vals, bars)):
        label    = f"~${round(val / 100) * 100:,.0f}"
        bar_w    = bar.get_width()
        # Inside if bar is wide enough (> 20% of max), else outside
        if bar_w > max_rev * 0.20:
            ax.text(bar_w - max_rev * 0.015, x[i], label,
                    ha="right", va="center", fontsize=9,
                    color="white", fontweight="600")
        else:
            ax.text(bar_w + max_rev * 0.01, x[i], label,
                    ha="left", va="center", fontsize=9,
                    color=TEXT, fontweight="600")

    ax.set_yticks(x)
    ax.set_yticklabels([ARCH_LABELS[a] for a in archs], color=TEXT, fontsize=9.5)
    ax.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda v, _: f"${v/1000:.0f}K" if v >= 1000 else f"${int(v)}")
    )
    ax.set_xlabel("Estimated monthly revenue at risk", color=TEXT_MUTED, fontsize=9, labelpad=8)
    ax.tick_params(axis="x", colors=TEXT_MUTED)

    ax.set_title(C2_TITLE,    color=TEXT,       fontsize=13, fontweight="bold", pad=14, loc="left")
    ax.set_xlabel(C2_SUBTITLE, color=TEXT_MUTED, fontsize=8.5, labelpad=10)

    plt.tight_layout()
    fig.savefig(C2_OUT, dpi=DPI, bbox_inches="tight", facecolor=BG)
    print(f"Saved: {C2_OUT}")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 3 — Churn reason share over time (trend lines)
# ─────────────────────────────────────────────────────────────────────────────

C3_TITLE    = "What's Driving Thesis Churn — and How It's Shifting"
C3_SUBTITLE = "Share of cancellations with a known reason, by quarter  ·  Thesis subscribers only"
C3_YLABEL   = "Share of cancellations"
C3_OUT      = Path(__file__).parent / "chart_3_trends.png"
C3_FIG_SIZE = (11, 6)
# Drop partial quarters (very low totals at boundaries)
C3_DROP_BEFORE = "2022-04-01"
C3_DROP_AFTER  = "2026-01-01"

def chart_3():
    # Pivot trend data
    by_period = defaultdict(lambda: defaultdict(int))
    for row in raw_trend:
        period = row["period"]
        arch   = row["archetype"]
        n      = row["n"]
        if period < C3_DROP_BEFORE or period > C3_DROP_AFTER:
            continue
        by_period[period][arch] += n

    periods_sorted = sorted(by_period.keys())
    dates = [datetime.strptime(p, "%Y-%m-%d") for p in periods_sorted]

    # Normalise to % share per period
    arch_shares = {a: [] for a in ARCH_ORDER_TREND}
    for period in periods_sorted:
        total = sum(by_period[period].values())
        for arch in ARCH_ORDER_TREND:
            share = by_period[period].get(arch, 0) / total * 100 if total else 0
            arch_shares[arch].append(share)

    fig, ax = plt.subplots(figsize=C3_FIG_SIZE, facecolor=BG)
    _apply_light_theme(ax)
    ax.yaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)

    for arch in ARCH_ORDER_TREND:
        shares = arch_shares[arch]
        color  = ARCH_COLORS[arch]
        ax.plot(dates, shares, color=color, linewidth=2.2, zorder=4,
                marker="o", markersize=3.5, markerfacecolor=color)

        # End label (right side)
        final_val = shares[-1]
        if final_val > 0.5:
            ax.text(dates[-1], final_val, f"  {ARCH_LABELS[arch]}  {final_val:.0f}%",
                    ha="left", va="center", fontsize=8.5,
                    color=color, fontweight="600")

    # X-axis: quarterly dates, labelled by year
    ax.set_xlim(dates[0], dates[-1] + (dates[-1] - dates[-2]) * 4)
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.tick_params(axis="x", colors=TEXT_MUTED, labelsize=8.5, rotation=30)

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylabel(C3_YLABEL, color=TEXT_MUTED, fontsize=9, labelpad=8)

    ax.set_title(C3_TITLE,    color=TEXT,       fontsize=13, fontweight="bold", pad=14, loc="left")
    ax.set_xlabel(C3_SUBTITLE, color=TEXT_MUTED, fontsize=8.5, labelpad=10)

    plt.tight_layout()
    fig.savefig(C3_OUT, dpi=DPI, bbox_inches="tight", facecolor=BG)
    print(f"Saved: {C3_OUT}")

# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────

chart_1()
chart_2()
chart_3()

if OPEN_AFTER:
    import subprocess
    for p in [C1_OUT, C2_OUT, C3_OUT]:
        subprocess.run(["open", str(p)])
