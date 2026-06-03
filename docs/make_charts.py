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
OPEN_CHARTS = [1, 4]   # which chart numbers to open in Preview after saving ([] = none)

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
    "fatigue":     "Product Overstock",
    "life_change": "Life Change",
    "involuntary": "Payment Declined",
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
C1_YLABEL    = "Subscribers (log scale)"
C1_FOOTNOTE  = "Low risk: P(churn) < 0.10   Medium risk: 0.10 to 0.50   High risk: > 0.50 (94 subscribers, all in Price — too few to show at scale)"
C1_OUT       = Path(__file__).parent / "chart_1_subscribers.png"
C1_FIG_SIZE  = (9, 5.5)
BAR_W        = 0.55

COLOR_LOW    = "#A8BFCF"   # warm slate blue — neutral, pleasant against amber
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

    # Low + medium only — high risk (94 subs, all Price) is invisible at log scale;
    # noted in the footnote instead
    ax.bar(x, low_vals,         BAR_W, color=COLOR_LOW,    zorder=3)
    ax.bar(x, med_vals, BAR_W, bottom=low_vals, color=COLOR_MEDIUM, zorder=3, alpha=0.92)

    # Log scale: makes small archetypes readable alongside Price
    ax.set_yscale("log")
    ax.set_ylim(bottom=0.05)
    ax.yaxis.set_major_formatter(
        ticker.FuncFormatter(lambda v, _: f"{v:.0f}K" if v >= 1 else f"{v*1000:.0f}")
    )

    # Total label just above each bar
    for i, (tot, arch) in enumerate(zip(totals_k, ARCH_ORDER_BAR)):
        raw = summary[arch]["total"]
        ax.text(x[i], tot * 1.15, f"{raw:,}", ha="center", va="bottom",
                fontsize=8.5, color=TEXT, fontweight="600")

    # Short callout: "X at risk" just above the medium+high band, close to the bar
    for i, arch in enumerate(ARCH_ORDER_BAR):
        med_hi = summary[arch]["medium"] + summary[arch]["high"]
        top_k  = totals_k[i]
        if med_hi > 0:
            ax.text(x[i] + BAR_W / 2 + 0.05, top_k * 1.0,
                    f"  {med_hi:,} at risk",
                    ha="left", va="center", fontsize=7.5, color=TEXT_MUTED)

    ax.set_xticks(x)
    ax.set_xticklabels([ARCH_LABELS[a] for a in ARCH_ORDER_BAR], color=TEXT, fontsize=9)
    ax.set_ylabel(C1_YLABEL, color=TEXT_MUTED, fontsize=9, labelpad=8)

    # No legend — footnote carries the definitions

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
C3_SUBTITLE = "Share of cancellations with a known reason, by quarter"
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
        raw_shares = arch_shares[arch]
        color      = ARCH_COLORS[arch]

        # 3-quarter rolling average — smooth without losing the overall trend
        window = 3
        smoothed = []
        for i in range(len(raw_shares)):
            lo = max(0, i - window // 2)
            hi = min(len(raw_shares), lo + window)
            smoothed.append(np.mean(raw_shares[lo:hi]))

        ax.plot(dates, smoothed, color=color, linewidth=2.2, zorder=4)

        final_val = smoothed[-1]
        if arch == "efficacy":
            # Mark the 2022 peak with a dot — presenter can speak to it
            peak_i = int(np.argmax(smoothed))
            ax.plot(dates[peak_i], smoothed[peak_i],
                    "o", color=color, markersize=7, zorder=5)
            end_label = "  Efficacy  0%"
        else:
            end_label = f"  {ARCH_LABELS[arch]}  {final_val:.0f}%"

        ax.text(dates[-1], final_val, end_label,
                ha="left", va="bottom", fontsize=8.5,
                color=color, fontweight="600", rotation=45,
                rotation_mode="anchor")

    import matplotlib.dates as mdates

    # X-axis ends at last data point — no phantom future
    # Add just enough right padding for end labels to breathe
    label_pad = (dates[-1] - dates[0]) * 0.04
    ax.set_xlim(dates[0], dates[-1] + label_pad)

    # Tick marks every 6 months; labels show year only at Jan ticks
    ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[7]))   # Jul tick marks only
    ax.xaxis.set_major_locator(mdates.YearLocator())               # Jan = year label
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.tick_params(axis="x", which="major", colors=TEXT_MUTED, labelsize=9, rotation=0)
    ax.tick_params(axis="x", which="minor", colors=TEXT_MUTED, length=4)

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylabel(C3_YLABEL, color=TEXT_MUTED, fontsize=9, labelpad=8)

    ax.set_title(C3_TITLE,    color=TEXT,       fontsize=13, fontweight="bold", pad=14, loc="left")
    ax.set_xlabel(C3_SUBTITLE, color=TEXT_MUTED, fontsize=8.5, labelpad=10)

    plt.tight_layout()
    fig.savefig(C3_OUT, dpi=DPI, bbox_inches="tight", facecolor=BG)
    print(f"Saved: {C3_OUT}")

# ─────────────────────────────────────────────────────────────────────────────
# CHART 4 — Urgency rate: % at risk within each archetype (lollipop)
# ─────────────────────────────────────────────────────────────────────────────

C4_TITLE    = "Where Intervention Is Most Urgent"
C4_SUBTITLE = "Share of subscribers in each churn-reason group flagged as medium-to-high risk"
C4_OUT      = Path(__file__).parent / "chart_4_urgency.png"
C4_FIG_SIZE = (9, 5)

def chart_4():
    # Sort archetypes by urgency rate descending
    archs = sorted(
        ARCH_ORDER_BAR,
        key=lambda a: (summary[a]["medium"] + summary[a]["high"]) / summary[a]["total"],
        reverse=True,
    )

    pct_vals   = [(summary[a]["medium"] + summary[a]["high"]) / summary[a]["total"] * 100
                  for a in archs]
    count_vals = [summary[a]["medium"] + summary[a]["high"] for a in archs]
    total_vals = [summary[a]["total"] for a in archs]
    colors     = [ARCH_COLORS[a] for a in archs]

    fig, ax = plt.subplots(figsize=C4_FIG_SIZE, facecolor=BG)
    _apply_light_theme(ax)
    ax.xaxis.grid(True, color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)

    y = np.arange(len(archs))

    for i, (pct, count, total, color) in enumerate(zip(pct_vals, count_vals, total_vals, colors)):
        ax.plot([0, pct], [y[i], y[i]], color=color, lw=2.0, zorder=3)
        ax.plot(pct, y[i], "o", color=color, markersize=10, zorder=4)
        # Percentage: right after the dot
        ax.text(pct + 1.5, y[i], f"{pct:.0f}%",
                ha="left", va="center", fontsize=12, color=color, fontweight="700")
        # Count: further right, clearly separated, smaller
        ax.text(pct + 9, y[i], f"{count:,} of {total:,}",
                ha="left", va="center", fontsize=8.5, color=TEXT_MUTED)

    ax.set_yticks(y)
    ax.set_yticklabels([ARCH_LABELS[a] for a in archs], color=TEXT, fontsize=10)
    ax.set_xlim(0, 115)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.tick_params(axis="x", colors=TEXT_MUTED, labelsize=9)
    ax.set_xlabel(C4_SUBTITLE, color=TEXT_MUTED, fontsize=8.5, labelpad=10)
    ax.set_title(C4_TITLE, color=TEXT, fontsize=13, fontweight="bold", pad=14, loc="left")

    plt.tight_layout()
    fig.savefig(C4_OUT, dpi=DPI, bbox_inches="tight", facecolor=BG)
    print(f"Saved: {C4_OUT}")


# ─────────────────────────────────────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────────────────────────────────────

charts = [(1, chart_1, C1_OUT), (2, chart_2, C2_OUT),
          (3, chart_3, C3_OUT), (4, chart_4, C4_OUT)]

import subprocess
for n, fn, out in charts:
    fn()
    if n in OPEN_CHARTS:
        subprocess.run(["open", str(out)])
