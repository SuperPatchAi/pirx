#!/usr/bin/env python3
"""Build the PIRX science paper as a two-column academic PDF.

Pulls exact formulas/constants from the README-verified codebase.
Target: 12-15 page publication-style document.
"""

from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    Paragraph,
    PageTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_PDF = ROOT / "docs" / "The_Science_Behind_PIRX.pdf"

PAGE_W, PAGE_H = A4  # 595.28 x 841.89 pt
MARGIN = 12 * mm  # 34 pt
USABLE_W = PAGE_W - 2 * MARGIN  # ~527 pt
GAP = 8 * mm  # ~23 pt
COL_W = (USABLE_W - GAP) / 2  # ~252 pt
TBL_W = COL_W - 4  # safe table content width (~248 pt)

DARK = colors.HexColor("#1a1a1a")
ACCENT = colors.HexColor("#2c5282")
LIGHT_BG = colors.HexColor("#f7f8fa")
ROW_ALT = colors.HexColor("#f0f4f8")
RULE_CLR = colors.HexColor("#9ca3af")
EQ_BG = colors.HexColor("#f0f2f5")

FONT_BODY = "Times-Roman"
FONT_BOLD = "Times-Bold"
FONT_ITAL = "Times-Italic"
FONT_MONO = "Courier"


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def _styles():
    return {
        "title": ParagraphStyle(
            "title", fontName=FONT_BOLD, fontSize=18, leading=22,
            alignment=TA_CENTER, spaceAfter=4, textColor=DARK,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName=FONT_ITAL, fontSize=10, leading=13,
            alignment=TA_CENTER, spaceAfter=6, textColor=DARK,
        ),
        "authors": ParagraphStyle(
            "authors", fontName=FONT_BODY, fontSize=10, leading=13,
            alignment=TA_CENTER, spaceAfter=2,
        ),
        "affil": ParagraphStyle(
            "affil", fontName=FONT_ITAL, fontSize=8.5, leading=11,
            alignment=TA_CENTER, spaceAfter=8,
        ),
        "abstract_head": ParagraphStyle(
            "abstract_head", fontName=FONT_BOLD, fontSize=9, leading=11,
            alignment=TA_CENTER, spaceAfter=3,
        ),
        "abstract": ParagraphStyle(
            "abstract", fontName=FONT_BODY, fontSize=9, leading=11.5,
            alignment=TA_JUSTIFY, leftIndent=20, rightIndent=20, spaceAfter=4,
        ),
        "keywords": ParagraphStyle(
            "keywords", fontName=FONT_BODY, fontSize=8, leading=10,
            alignment=TA_CENTER, spaceAfter=10,
        ),
        "h1": ParagraphStyle(
            "h1", fontName=FONT_BOLD, fontSize=11, leading=13,
            spaceBefore=14, spaceAfter=5, textColor=ACCENT,
        ),
        "h2": ParagraphStyle(
            "h2", fontName=FONT_BOLD, fontSize=9.5, leading=11.5,
            spaceBefore=7, spaceAfter=3, textColor=DARK,
        ),
        "body": ParagraphStyle(
            "body", fontName=FONT_BODY, fontSize=8.8, leading=11.5,
            alignment=TA_JUSTIFY, spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName=FONT_BODY, fontSize=8.5, leading=11,
            leftIndent=10, firstLineIndent=-8, spaceAfter=3,
        ),
        "caption": ParagraphStyle(
            "caption", fontName=FONT_ITAL, fontSize=7.5, leading=9.5,
            alignment=TA_CENTER, spaceAfter=6,
        ),
        "eq_text": ParagraphStyle(
            "eq_text", fontName=FONT_MONO, fontSize=7.8, leading=10.5,
            alignment=TA_LEFT, leftIndent=4,
        ),
        "eq_num": ParagraphStyle(
            "eq_num", fontName=FONT_BODY, fontSize=8, leading=10.5,
            alignment=TA_RIGHT,
        ),
        "ref": ParagraphStyle(
            "ref", fontName=FONT_BODY, fontSize=7.5, leading=9.5,
            spaceAfter=2,
        ),
        "tbl_cell": ParagraphStyle(
            "tbl_cell", fontName=FONT_BODY, fontSize=6.5, leading=8.5,
        ),
        "tbl_head": ParagraphStyle(
            "tbl_head", fontName=FONT_BOLD, fontSize=6.8, leading=8.8,
            textColor=colors.white,
        ),
    }


ST = _styles()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _p(text, style_key="body"):
    return Paragraph(text, ST[style_key])


def _ps(texts, style_key="body"):
    return [Paragraph(t, ST[style_key]) for t in texts]


def _hr(width=COL_W):
    d = Drawing(width, 5)
    d.add(Line(0, 2.5, width, 2.5, strokeColor=ACCENT, strokeWidth=0.5))
    return d


def _eq(formula, num):
    """Numbered equation block with left accent stripe."""
    t = Table(
        [[Paragraph(formula, ST["eq_text"]),
          Paragraph(f"({num})", ST["eq_num"])]],
        colWidths=[TBL_W - 28, 28],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), EQ_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (0, 0), 8),
        ("RIGHTPADDING", (-1, -1), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBEFORESTYLE", (0, 0), (0, -1)),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, ACCENT),
    ]))
    return t


def _tbl(data, widths, caption=None):
    """Column-width table with accent header and optional caption."""
    wrapped = []
    for ri, row in enumerate(data):
        st = "tbl_head" if ri == 0 else "tbl_cell"
        wrapped.append([Paragraph(str(c), ST[st]) for c in row])
    t = Table(wrapped, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, ACCENT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))
    elems = [t]
    if caption:
        elems.append(Paragraph(caption, ST["caption"]))
    return KeepTogether(elems)


def _fig_pipeline():
    """End-to-end pipeline box diagram scaled for column width."""
    w = COL_W
    d = Drawing(w, 75)
    bw, bh = 42, 18
    labels = ["Ingest", "Clean", "Features", "Project", "Persist"]
    spacing = (w - len(labels) * bw) / (len(labels) - 1)
    for i, lbl in enumerate(labels):
        x = i * (bw + spacing)
        d.add(Rect(x, 38, bw, bh, strokeColor=DARK, fillColor=colors.white, strokeWidth=0.5))
        d.add(String(x + bw / 2, 44, lbl, textAnchor="middle", fontName=FONT_BODY, fontSize=6.5))
        if i < len(labels) - 1:
            ax = x + bw
            d.add(Line(ax, 47, ax + spacing, 47, strokeColor=DARK, strokeWidth=0.4))
    d.add(Rect(w * 0.18, 6, w * 0.64, 16, strokeColor=DARK, fillColor=colors.white, strokeWidth=0.5))
    d.add(String(w / 2, 11, "APIs / Frontend / Chat / Realtime", textAnchor="middle", fontName=FONT_BODY, fontSize=6))
    last_x = (len(labels) - 1) * (bw + spacing)
    d.add(Line(last_x + bw / 2, 38, w / 2, 22, strokeColor=DARK, strokeWidth=0.4))
    return d


def _fig_orchestrator():
    """Model orchestration and fallback diagram with GB and LSTM paths."""
    w = COL_W
    d = Drawing(w, 92)
    d.add(Rect(4, 62, 68, 18, strokeColor=DARK, fillColor=colors.white, strokeWidth=0.5))
    d.add(String(38, 68, "Orchestrator", textAnchor="middle", fontName=FONT_BODY, fontSize=6.5))
    d.add(Rect(90, 68, 65, 14, strokeColor=DARK, fillColor=colors.white, strokeWidth=0.5))
    d.add(String(122, 72, "deterministic", textAnchor="middle", fontName=FONT_BODY, fontSize=6))
    d.add(Rect(90, 48, 65, 14, strokeColor=DARK, fillColor=colors.white, strokeWidth=0.5))
    d.add(String(122, 52, "GB (per-user)", textAnchor="middle", fontName=FONT_BODY, fontSize=6))
    d.add(Rect(90, 28, 65, 14, strokeColor=DARK, fillColor=colors.white, strokeWidth=0.5))
    d.add(String(122, 32, "LSTM (gated)", textAnchor="middle", fontName=FONT_BODY, fontSize=6))
    d.add(Rect(170, 28, 65, 14, strokeColor=DARK, fillColor=colors.white, strokeWidth=0.5))
    d.add(String(202, 32, "LSTM adapter", textAnchor="middle", fontName=FONT_BODY, fontSize=6))
    d.add(Rect(170, 6, 75, 14, strokeColor=DARK, fillColor=colors.white, strokeWidth=0.5))
    d.add(String(207, 10, "fallback -> determ.", textAnchor="middle", fontName=FONT_BODY, fontSize=6))
    d.add(Line(72, 74, 90, 74, strokeColor=DARK, strokeWidth=0.4))
    d.add(Line(72, 70, 90, 54, strokeColor=DARK, strokeWidth=0.4))
    d.add(Line(72, 66, 90, 34, strokeColor=DARK, strokeWidth=0.4))
    d.add(Line(155, 34, 170, 34, strokeColor=DARK, strokeWidth=0.4))
    d.add(Line(202, 28, 202, 20, strokeColor=DARK, strokeWidth=0.4))
    return d


def _fig_uncertainty():
    """Supported range composition diagram."""
    w = COL_W
    d = Drawing(w, 68)
    boxes = [("Base\n1.5%", 4), ("Volatility\nterm", 66), ("Data quality\nterm", 128), ("ACWR\nterm", 190)]
    bw = 56
    for label, x in boxes:
        d.add(Rect(x, 34, bw, 22, strokeColor=DARK, fillColor=colors.white, strokeWidth=0.5))
        lines = label.split("\n")
        d.add(String(x + bw / 2, 46, lines[0], textAnchor="middle", fontName=FONT_BODY, fontSize=6))
        if len(lines) > 1:
            d.add(String(x + bw / 2, 38, lines[1], textAnchor="middle", fontName=FONT_BODY, fontSize=6))
    for x in [60, 122, 184]:
        d.add(Line(x, 45, x + 6, 45, strokeColor=DARK, strokeWidth=0.4))
    d.add(Rect(70, 6, 110, 16, strokeColor=DARK, fillColor=colors.white, strokeWidth=0.5))
    d.add(String(125, 11, "total_pct -> range", textAnchor="middle", fontName=FONT_BODY, fontSize=6))
    d.add(Line(125, 34, 125, 22, strokeColor=DARK, strokeWidth=0.4))
    return d


# ---------------------------------------------------------------------------
# Page templates and footer
# ---------------------------------------------------------------------------

def _on_page(canvas, _doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE_CLR)
    canvas.setLineWidth(0.3)
    canvas.line(MARGIN, 9.5 * mm, PAGE_W - MARGIN, 9.5 * mm)
    canvas.setFont(FONT_BODY, 7)
    canvas.setFillColor(RULE_CLR)
    canvas.drawString(MARGIN, 6.5 * mm, "The Science Behind PIRX")
    canvas.drawRightString(PAGE_W - MARGIN, 6.5 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Content sections
# ---------------------------------------------------------------------------

def _title_page():
    s = []
    s.append(Spacer(1, 18))
    s.append(_p("The Science Behind PIRX", "title"))
    s.append(_p(
        "Deterministic Projection Architecture with Controlled ML "
        "Personalization for Running Performance Forecasting", "subtitle"))
    s.append(Spacer(1, 6))
    s.append(_p("PIRX Engineering", "authors"))
    s.append(_p("Performance Intelligence Rx", "affil"))
    s.append(Spacer(1, 10))
    s.append(_p("ABSTRACT", "abstract_head"))
    s.extend(_ps([
        "PIRX forecasts race performance by combining deterministic equations "
        "with trained machine-learning personalization. The system ingests "
        "wearable training data, applies domain-specific cleaning gates, computes "
        "rolling features across five physiological domains, and produces bounded "
        "projections with explicit uncertainty semantics. This paper documents "
        "every formula in the active codebase, explains the design rationale "
        "behind each modeling choice, and maps the rollout architecture that "
        "governs transitions from deterministic to ML-based serving.",

        "The central contribution is architectural: interpretability and safety "
        "are treated as first-order constraints, not post-hoc additions. Every "
        "projection update is traceable to a named equation path, a bounded "
        "uncertainty interval, and metadata describing which model produced it. "
        "ML components — per-user Gradient Boosting projection (scikit-learn), "
        "LSTM temporal models (PyTorch), SHAP TreeExplainer for driver attribution, "
        "K-Means clustering for training type classification, DTW-based trajectory "
        "matching (dtaidistance), Optuna hyperparameter optimization, Random Forest "
        "injury risk, and GradientBoosting readiness classification — are "
        "introduced through explicit feature flags, cohort gating, and auditable "
        "fallback behavior rather than silent model replacement.",

        "The paper proceeds through data conditioning, feature engineering, "
        "baseline estimation, projection equations, event scaling, readiness "
        "scoring, and model orchestration. Each section states the exact "
        "computation, the constants used, the failure modes mitigated, and "
        "the rationale linking the engineering choice to a product or safety "
        "goal. Limitations are declared directly, and implementation status "
        "is labeled explicitly as active, rollout-gated, or non-primary.",

        "We present 87 numbered equations covering feature engineering, "
        "projection computation, gradient boosting and LSTM personalization, "
        "event scaling, readiness decomposition, injury risk calibration, "
        "DTW-based trajectory prediction, and accuracy monitoring. A complete "
        "formula catalog, implementation status matrix, and terminology "
        "glossary are provided as appendices. The document is organized as "
        "a self-contained technical reference that can be validated against "
        "the codebase at any point in time.",
    ], "abstract"))
    s.append(Spacer(1, 4))
    s.append(_p(
        "<b>Keywords:</b> running performance prediction, race projection, "
        "training load, ACWR, Riegel scaling, EWMA, readiness scoring, "
        "model orchestration, rollout safety, wearable data, deterministic "
        "projection, driver decomposition, uncertainty quantification",
        "keywords"))
    s.append(_hr(USABLE_W))
    return s


def _sec_intro():
    s = []
    s.append(_p("1. Introduction", "h1"))
    s.extend(_ps([
        "Predicting race performance from training data is a problem with "
        "decades of applied research [1-3] yet persistent practical gaps. "
        "Most commercial tools either provide opaque ML scores that cannot "
        "be inspected, or simple pace calculators that ignore physiological "
        "context. Runners and coaches face a specific frustration: they can "
        "see their training data, but they cannot connect it to a defensible "
        "estimate of what that training structurally supports.",

        "PIRX addresses this by designing around <i>interpretability "
        "first</i>: every output is traceable to a named formula, bounded by "
        "explicit uncertainty logic, and annotated with model-provenance "
        "metadata. The system objective is to answer a specific question: "
        "<i>what does current training structurally support right now, and "
        "why?</i> This is deliberately not a forecast of race-day outcome, "
        "which depends on pacing, weather, terrain, and taper execution. "
        "It is an estimate of current aerobic and structural capability "
        "derived from observable training signals.",

        "The distinction between capability estimation and race prediction "
        "is central. Capability changes slowly with training adaptation; "
        "race-day outcome is volatile. By anchoring to capability, PIRX "
        "can provide stable, interpretable updates that reflect genuine "
        "structural changes rather than noise or day-to-day variation.",

        "PIRX operates a five-stage pipeline: wearable data ingestion, "
        "cleaning and quality gating, feature engineering across five "
        "physiological domains, projection computation with driver "
        "decomposition, and persistence to APIs, realtime streams, and "
        "a conversational agent. Each stage gates the next, ensuring "
        "that downstream computations operate on validated inputs. "
        "This pipeline-first architecture means that a bad sensor reading "
        "cannot silently propagate to a user-facing projection change.",

        "This paper makes three contributions: (1) a complete formula "
        "catalog of 87 numbered equations aligned to the active codebase; "
        "(2) a narrative account of why each modeling choice was made, "
        "linking equations to product safety goals; and (3) a description "
        "of the rollout architecture that governs phased transitions from "
        "deterministic to ML-based projection serving. The paper structure "
        "follows standard methods reporting: architecture, data conditioning, "
        "feature engineering, modeling, evaluation, and limitations.",
    ]))

    s.append(_p("1.1 Related work", "h2"))
    s.extend(_ps([
        "Power-law models for endurance performance prediction date to "
        "Riegel [1], who demonstrated that race times across distances "
        "follow T2 = T1 * (D2/D1)^k with a population exponent near 1.06. "
        "Subsequent work by Blythe and Kiraly [2] extended this with "
        "low-rank matrix completion approaches that learn individual "
        "exponents from sparse multi-distance race histories, achieving "
        "strong accuracy with minimal input data.",

        "Dash [3] provided a generalized framework for running performance "
        "prediction incorporating environmental adjustment and training "
        "load context, demonstrating that model accuracy improves when "
        "physiological features complement simple distance-time scaling. "
        "Chang et al. [4] explored deep learning for fatigue stage "
        "classification from wearable IMU data, relevant to PIRX's "
        "readiness and injury-risk components.",

        "PIRX differs from these approaches in emphasis. Where academic "
        "models optimize for predictive accuracy on held-out test sets, "
        "PIRX optimizes for <i>interpretable stability</i> in a production "
        "context. Every equation must be explainable to a non-technical "
        "user through named drivers and bounded ranges. Every model "
        "transition must be reversible through explicit rollout controls. "
        "This places architectural constraints (dampening, shift thresholds, "
        "decomposition closure) that reduce raw predictive flexibility "
        "but increase user trust and operational safety.",

        "The system borrows specific techniques from the literature: "
        "Riegel scaling for cross-distance transfer [1], EWMA for load "
        "smoothing [4], matched-HR efficiency metrics from exercise "
        "physiology, Gradient Boosting and LSTM regression for per-user "
        "projection personalization, Random Forest and Gradient Boosting "
        "classification for injury risk and readiness, SHAP TreeExplainer "
        "for driver attribution, K-Means clustering for training type "
        "detection, Dynamic Time Warping for trajectory matching, and "
        "Optuna for hyperparameter optimization. These are composed within "
        "a pipeline architecture that prioritizes deterministic behavior "
        "and explicit fallback.",
    ]))
    s.append(_hr())
    return s


def _sec_pipeline():
    s = []
    s.append(_p("2. System Architecture", "h1"))
    s.extend(_ps([
        "PIRX uses a FastAPI backend with Celery task queues backed by "
        "Redis, a Supabase PostgreSQL database for persistence and "
        "realtime subscriptions, and a Next.js frontend with App Router. "
        "Wearable data enters via OAuth provider connections (Strava, "
        "Garmin via Terra API) or webhook-driven incremental sync.",

        "The pipeline is intentionally sequential: cleaning gates fire "
        "before feature computation, features must be current before "
        "projection recompute executes, and projection state must be "
        "persisted before any API or realtime consumer can access it. "
        "This ordering is not an implementation convenience; it is a "
        "design invariant that prevents downstream contamination.",

        "Figure 1 shows the end-to-end flow. The architecture produces "
        "a single source of computational truth that all consumer layers "
        "(REST APIs, Supabase Realtime subscriptions, LangGraph chat "
        "tools) read from. No consumer modifies projection state; they "
        "only read persisted snapshots with attached metadata.",
    ]))
    s.append(_fig_pipeline())
    s.append(_p(
        "Figure 1. PIRX data flow from wearable ingestion through "
        "cleaning, feature engineering, projection, and consumer exposure.",
        "caption"))

    s.append(_p("2.1 Technology stack", "h2"))
    s.append(_tbl(
        [
            ["Layer", "Technology", "Role"],
            ["API", "FastAPI (Python)", "Request handling, auth, routing"],
            ["Task queue", "Celery + Redis", "Async feature/projection recompute"],
            ["Database", "Supabase PostgreSQL", "Persistence, auth, realtime"],
            ["Frontend", "Next.js (App Router)", "UI rendering, realtime subscriptions"],
            ["Integrations", "Strava OAuth, Terra API", "Wearable data ingestion"],
            ["ML serving", "Python (scikit-learn, PyTorch)", "Model inference + lifecycle"],
            ["Chat", "LangGraph + OpenAI", "Conversational agent with tools"],
        ],
        [0.20 * TBL_W, 0.34 * TBL_W, 0.46 * TBL_W],
        "Table 0. Technology stack summary."
    ))
    s.append(_hr())
    return s


def _sec_cleaning():
    s = []
    s.append(_p("3. Data Conditioning", "h1"))
    s.append(_p("3.1 Cleaning rules", "h2"))
    s.extend(_ps([
        "Every activity passes through a filter chain before entering "
        "feature computation. The rules target specific failure modes: "
        "sensor artifacts, non-running sessions, implausible pace records, "
        "and low-information short efforts. The chain is ordered so that "
        "the cheapest checks (type, duration) execute first.",
    ]))
    s.append(_tbl(
        [
            ["Filter", "Rule", "Rationale"],
            ["Activity type", "easy / threshold / interval / race", "Exclude non-running sessions"],
            ["Non-race min", "dur >= 180s, dist >= 1600m", "Remove trivial recordings"],
            ["Race min", "dur >= 60s, dist >= 400m", "Retain short race efforts"],
            ["Pace floor", "pace >= 223 s/km", "Reject sensor/GPS glitches"],
            ["Pace ceiling", "pace <= 900 s/km", "Remove walk/stop artifacts"],
            ["Relative outlier", "pace <= 1.5 * avg_pace", "Personalized outlier suppression"],
            ["Elevation quality", "reject if dist > 10km, elev = 0", "Barometer failure detection"],
        ],
        [0.26 * TBL_W, 0.40 * TBL_W, 0.34 * TBL_W],
        "Table 1. Activity cleaning gates applied before feature computation."
    ))
    s.append(_p("3.2 Pace normalization", "h2"))
    s.extend(_ps([
        "When pace is absent from the provider payload, it is derived from "
        "duration and distance. The runner's average pace is computed from "
        "at least three prior valid activities. The relative outlier gate "
        "activates only after enough data exists to form a reliable average, "
        "preventing early sessions from being incorrectly rejected.",

        "The elevation quality filter specifically targets barometric sensor "
        "failures common in older wearable devices. A long outdoor run with "
        "zero elevation gain is almost certainly a data artifact. Treadmill "
        "and indoor runs are exempted since zero elevation is expected.",
    ]))
    s.append(_p("3.3 Design rationale", "h2"))
    s.extend(_ps([
        "The cleaning chain is deliberately aggressive. In projection "
        "systems, it is safer to discard a valid session than to include "
        "an invalid one, because a single corrupt session can shift "
        "rolling features and propagate noise into driver scores and "
        "projections. The minimum distance threshold of 1600m for "
        "non-race activities corresponds to approximately one mile and "
        "filters sessions too short to carry meaningful aerobic signal.",

        "The pace bounds (223-900 sec/km) correspond to approximately "
        "3:43/km to 15:00/km. The lower bound is faster than world-record "
        "marathon pace, so legitimate running sessions will not be rejected. "
        "The upper bound excludes walking-pace activities that providers "
        "sometimes misclassify as runs.",
    ]))
    s.append(_hr())
    return s


def _sec_features():
    s = []
    s.append(_p("4. Feature Engineering", "h1"))
    s.append(_p("4.1 Temporal weighting", "h2"))
    s.extend(_ps([
        "Features are aggregated across three windows with asymmetric weights "
        "that prioritize recent training while preserving structural context "
        "from the preceding mesocycle. The composite score is:",
    ]))
    s.append(_eq("W = 0.45 * W_7d + 0.35 * W_8-21d + 0.20 * W_22-90d", 1))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "The 7-day window carries the strongest signal because acute training "
        "changes are the most informative predictor of near-term capability "
        "shifts. The 22-90 day anchor prevents overreaction to single-week "
        "anomalies and preserves the base training structure in the score.",
    ]))

    s.append(_p("4.2 Volume features", "h2"))
    s.extend(_ps([
        "Volume is measured as cumulative distance across four standard "
        "windows. These raw sums feed both the volume driver and the "
        "load-consistency calculations:",
    ]))
    s.append(_eq("rolling_distance_Nd = sum(dist_m, last N days)   N in {7, 21, 42, 90}", 2))
    s.append(Spacer(1, 2))
    s.append(_eq("sessions_per_week = count(activities, last 7 days)", 3))
    s.append(Spacer(1, 2))
    s.append(_eq("long_run_count = count(dist_m >= 15000, last 42 days)", 4))
    s.append(Spacer(1, 3))

    s.append(_p("4.3 Intensity distribution", "h2"))
    s.extend(_ps([
        "Heart-rate zone proportions characterize training polarity. Zone "
        "time is normalized to remove confounding from variable weekly volume. "
        "Threshold density and speed exposure are expressed as weekly-normalized "
        "minutes to allow cross-week comparison:",
    ]))
    s.append(_eq("zN_pct = zone_time_N / total_zone_time   (21-day window)", 5))
    s.append(Spacer(1, 2))
    s.append(_eq("threshold_density = (z4_seconds / 60) / 3   [min/wk]", 6))
    s.append(Spacer(1, 2))
    s.append(_eq("speed_exposure = (z5_seconds / 60) / 3   [min/wk]", 7))
    s.append(Spacer(1, 3))

    s.append(_p("4.4 Efficiency metrics", "h2"))
    s.extend(_ps([
        "Running economy is assessed by pace at matched heart-rate demand "
        "rather than absolute pace, isolating fitness gains from temporary "
        "effort strategy changes:",
    ]))
    s.append(_eq("matched_hr_pace = mean(pace where 140 <= avg_hr <= 155)", 8))
    s.append(Spacer(1, 2))
    s.append(_eq("hr_drift = mean((half2_pace - half1_pace) / half1_pace)", 9))
    s.append(Spacer(1, 2))
    s.append(_eq("pace_decay = mean((last_qtr - first_half) / first_half)", 10))
    s.append(Spacer(1, 3))

    s.append(_p("4.5 Consistency metrics", "h2"))
    s.extend(_ps([
        "Consistency features are dispersion metrics rather than means, "
        "because adaptation reliability is better explained by variance "
        "control than by peak workload events:",
    ]))
    s.append(_eq("weekly_load_stddev = std(weekly_dist over 6 weeks)", 11))
    s.append(Spacer(1, 2))
    s.append(_eq("block_variance = var(14-day_dist over 3 blocks)", 12))
    s.append(Spacer(1, 2))
    s.append(_eq("session_stability = std(weekly_session_ct over 6 wks)", 13))
    s.append(Spacer(1, 3))

    s.append(_p("4.6 ACWR with EWMA smoothing", "h2"))
    s.extend(_ps([
        "The acute-to-chronic workload ratio uses exponentially weighted "
        "moving averages rather than naive rolling means, improving stability "
        "at window boundaries [4]. Three window pairs capture different "
        "horizons of load balance:",
    ]))
    s.append(_eq("alpha = 2 / (window_days + 1)", 14))
    s.append(Spacer(1, 2))
    s.append(_eq("EWMA_t = alpha * load_t + (1 - alpha) * EWMA_(t-1)", 15))
    s.append(Spacer(1, 2))
    s.append(_eq("EWMA_0 = load_0", 16))
    s.append(Spacer(1, 2))
    s.extend(_ps([
        "The EWMA is seeded with the first observed daily load rather than "
        "a population or non-zero mean, following standard EWMA convention "
        "and avoiding systematic bias for infrequent trainers.",
    ]))
    s.append(_eq("ACWR = acute_load / chronic_load", 17))
    s.append(Spacer(1, 2))
    s.append(_tbl(
        [
            ["ACWR variant", "Acute window", "Chronic window"],
            ["acwr_4w", "7 days", "28 days"],
            ["acwr_6w", "7 days", "42 days"],
            ["acwr_8w", "7 days", "56 days"],
        ],
        [0.34 * TBL_W, 0.33 * TBL_W, 0.33 * TBL_W],
        "Table 2. ACWR window configurations."
    ))

    s.append(_p("4.7 Physiological trends", "h2"))
    s.extend(_ps([
        "When available from wearable providers, physiological signals "
        "(resting HR trend, HRV trend, sleep quality) are incorporated as "
        "directional indicators. These features are used opportunistically: "
        "uncertainty terms compensate when they are missing, preventing "
        "accidental optimism in sparse-data scenarios.",

        "Sleep and body data arrive via Terra webhook integration. "
        "Normalized payloads are persisted to a physiology table and "
        "consumed by readiness scoring. The readiness engine uses trend "
        "direction (improving/declining) rather than absolute values, "
        "which accommodates inter-individual differences in resting HR "
        "and HRV ranges.",
    ]))

    s.append(_tbl(
        [
            ["Domain", "Key features", "Equation type"],
            ["Volume", "rolling_distance_{7,21,42,90}d, long_run_count", "Windowed sums (Eq. 2-4)"],
            ["Intensity", "zN_pct, threshold_density, speed_exposure", "Normalized ratios (Eq. 5-7)"],
            ["Efficiency", "matched_hr_pace, hr_drift, pace_decay", "Matched-demand comparison (Eq. 8-10)"],
            ["Consistency", "load_stddev, block_variance, session_stability", "Dispersion metrics (Eq. 11-13)"],
            ["Physiology", "resting_hr_trend, hrv_trend, sleep_score", "Trend direction indicators"],
        ],
        [0.22 * TBL_W, 0.40 * TBL_W, 0.38 * TBL_W],
        "Table 3. Feature domain summary with equation cross-references."
    ))

    s.append(_p("4.8 Feature design rationale", "h2"))
    s.extend(_ps([
        "The five-domain structure was chosen because it maps directly "
        "to coaching language. When a coach reviews an athlete's training, "
        "they naturally assess volume (are you running enough?), intensity "
        "(are you running hard enough, and in the right zones?), efficiency "
        "(are you getting faster at the same effort?), consistency (are "
        "you training regularly without large gaps or spikes?), and "
        "physiology (is your body recovering between sessions?).",

        "Each domain captures a different mechanism of training adaptation. "
        "Volume drives central cardiovascular adaptations (increased stroke "
        "volume, capillary density). Intensity drives peripheral adaptations "
        "(lactate threshold, VO2max). Efficiency captures neuromuscular "
        "improvements (running economy, stride mechanics). Consistency "
        "reflects the compounding effect of regular stimulus. Physiology "
        "monitors the recovery substrate that enables adaptation.",

        "The asymmetric temporal weighting (0.45/0.35/0.20) is motivated "
        "by the observation that recent training predicts near-term "
        "capability better than older training, but abrupt changes in "
        "a single week are often noise. The three-window structure smooths "
        "this: the 7-day window captures current state, the 8-21 day "
        "window captures the current training block, and the 22-90 day "
        "window anchors to the underlying training base.",

        "Feature defaults are intentionally conservative. When a feature "
        "cannot be computed (insufficient data, missing HR zones), it "
        "defaults to a neutral value (score 50) rather than an optimistic "
        "estimate. This means sparse data degrades the projection toward "
        "the baseline rather than inflating it, which is the safer failure "
        "mode for users making training decisions based on the output.",
    ]))
    s.append(_hr())
    return s


def _sec_baseline():
    s = []
    s.append(_p("5. Baseline Estimation", "h1"))
    s.extend(_ps([
        "The projection engine computes improvement relative to a 5K baseline "
        "anchor. Because users arrive with widely varying data histories, "
        "PIRX uses a tiered fallback chain that degrades gracefully from "
        "high-confidence race results to conservative defaults:",
    ]))
    s.append(_tbl(
        [
            ["Tier", "Source", "Calculation", "Confidence"],
            ["1", "Detected race", "Race result (non-5K scaled via Riegel)", "Highest"],
            ["2", "Sustained effort", "Riegel-scaled to 5K (dist >= 3km, hr_pct >= 0.85)", "High"],
            ["3", "P10 pace", "p10_pace * 5 * 0.96", "Moderate"],
            ["4", "Median pace", "median_pace * 5 * 0.80", "Low"],
            ["5", "Default", "1500 s (25:00 5K)", "Lowest"],
        ],
        [0.08 * TBL_W, 0.22 * TBL_W, 0.46 * TBL_W, 0.24 * TBL_W],
        "Table 4. Baseline estimation tiers with fallback chain."
    ))
    s.append(_p("5.1 Race detection criteria", "h2"))
    s.extend(_ps([
        "Tier 1 applies strict heuristics to identify race-quality efforts. "
        "The activity must fall within canonical distance windows "
        "(1500/3000/5000/10000/half/marathon), show heart-rate engagement "
        "above 83% of estimated maximum, and achieve pace faster than a "
        "cohort p25 threshold. Non-5K races are converted to 5K-equivalent "
        "times using the Riegel formula (Section 7).",
    ]))
    s.extend(_ps([
        "Non-5K sustained efforts are projected to 5K-equivalent times "
        "using the Riegel power law (Section 7) rather than linear pace "
        "extrapolation, improving accuracy for activities at distances "
        "where the pace-to-race relationship is nonlinear.",
    ]))
    s.append(_eq("hr_pct = avg_hr / estimated_max_hr >= 0.83", 18))
    s.append(Spacer(1, 3))

    s.append(_p("5.2 KNN cold-start", "h2"))
    s.extend(_ps([
        "When no tier 1-4 data exists, a KNN cold-start estimator queries "
        "the reference population table to find the nearest baseline from "
        "demographic or activity-profile features. This reduces reliance on "
        "the 25:00 default for new users and provides a more plausible "
        "starting anchor for projection computation.",
    ]))

    s.append(_p("5.3 Baseline design rationale", "h2"))
    s.extend(_ps([
        "The tiered fallback chain embodies a principle: use the highest-"
        "confidence signal available, and degrade gracefully when it is "
        "absent. A runner who recently raced a 10K has a highly confident "
        "baseline (scale the result to 5K using Riegel). A runner who has "
        "never raced but runs regularly has a moderately confident baseline "
        "(percentile-discounted pace). A brand-new user has a low-confidence "
        "default that the system improves as data arrives.",

        "The discount factors (0.96 for P10, 0.80 for median) account for "
        "the gap between training pace and race-equivalent pace. Training "
        "runs are typically slower than race efforts; the discounts convert "
        "training data to estimated race capability. The P10 discount is "
        "smaller because the fastest 10% of training runs are already "
        "closer to race effort.",

        "Race detection requires multiple criteria (distance range, HR "
        "engagement, pace threshold) rather than a simple flag because "
        "provider labels are unreliable. Some platforms label every "
        "ParkRun as a 'run' without a race flag; some label training time "
        "trials as races. The multi-criterion approach reduces false "
        "positives that would corrupt the baseline anchor.",

        "The 25:00 default (1500 seconds) corresponds to approximately "
        "5:00/km pace for 5K, which is near the median finishing time for "
        "recreational 5K participants. This default is intentionally "
        "conservative: starting too fast (an optimistic baseline) would "
        "compress the improvement range and understate early gains, while "
        "starting too slow creates room for the projection to improve as "
        "real data replaces the default.",
    ]))
    s.append(_hr())
    return s


def _sec_projection():
    s = []
    s.append(_p("6. Projection Engine", "h1"))
    s.extend(_ps([
        "The projection engine converts feature vectors into a projected "
        "time, supported range, and driver contribution decomposition. "
        "It is the computational core of PIRX and is designed for three "
        "properties: interpretability (outputs trace to named drivers), "
        "stability (dampening and shift thresholds prevent noise propagation), "
        "and bounded optimism (caps prevent unrealistic improvement claims).",
    ]))

    s.append(_p("6.1 Driver scoring", "h2"))
    s.extend(_ps([
        "Each feature is normalized into a 0-100 driver score. The normalization "
        "compares the feature value against the baseline and clips the result. "
        "Inverse features (where lower values indicate improvement, such as "
        "pace or HR drift) use a reflected ratio:",
    ]))
    s.append(_eq("ratio = value / baseline", 19))
    s.append(Spacer(1, 2))
    s.append(_eq("ratio_inv = 2 - min(ratio, 2)   [inverse features]", 20))
    s.append(Spacer(1, 2))
    s.append(_eq("feature_score = clip(50 * ratio, 0, 100)", 21))
    s.append(Spacer(1, 2))
    s.append(_eq("driver_score = mean(feature_scores)   [default 50]", 22))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "ACWR is scored using U-shaped normalization centered at the "
        "optimal ratio of 1.05. Values near 1.05 score 100; values "
        "deviating by 0.5 or more score 0. This reflects the established "
        "finding that both overreaching (ACWR > 1.3) and detraining "
        "(ACWR &lt; 0.8) impair performance readiness [4]. NaN-valued "
        "features are excluded from scoring to prevent silent corruption "
        "of driver scores.",
    ]))
    s.append(_eq("acwr_score = clip(100*(1 - min(|acwr-1.05|/0.5, 1)), 0, 100)", 23))
    s.append(Spacer(1, 3))

    s.append(_p("6.2 Weighted aggregation", "h2"))
    s.extend(_ps([
        "Five structural drivers are weighted to reflect their relative "
        "contribution to running performance. Aerobic base carries the "
        "highest weight because sustained aerobic development is the "
        "strongest predictor of endurance capability across distances [2]:",
    ]))
    s.append(_tbl(
        [
            ["Driver", "Weight", "Primary features"],
            ["Aerobic base", "0.30", "Volume, long run count, sessions/week"],
            ["Threshold density", "0.25", "Z4 minutes/week, threshold sessions"],
            ["Speed exposure", "0.15", "Z5 minutes/week, interval sessions"],
            ["Running economy", "0.15", "Matched-HR pace, HR drift, pace decay"],
            ["Load consistency", "0.15", "Load stddev, block var., session stability"],
        ],
        [0.28 * TBL_W, 0.12 * TBL_W, 0.60 * TBL_W],
        "Table 5. Driver weights and mapped features."
    ))
    s.append(_eq("weighted_sum = sum(driver_score_d * weight_d)", 24))
    s.append(Spacer(1, 3))

    s.append(_p("6.3 Improvement calculation", "h2"))
    s.extend(_ps([
        "The improvement factor converts the aggregate driver score into "
        "a time delta relative to baseline. The factor is centered at zero "
        "when all drivers score 50 (neutral), and is capped to prevent "
        "unrealistic claims. A 25% maximum improvement cap means that "
        "even perfect feature scores cannot claim more than a quarter "
        "reduction from baseline time:",
    ]))
    s.append(_eq("improvement_factor = (weighted_sum - 50) / 50", 25))
    s.append(Spacer(1, 2))
    s.append(_eq("max_improvement = baseline_time * 0.25", 26))
    s.append(Spacer(1, 2))
    s.append(_eq("total_improvement = improvement_factor * max_improvement", 27))
    s.append(Spacer(1, 2))
    s.append(_eq("raw_projected = max(baseline - total_improvement, 60)", 28))
    s.append(Spacer(1, 3))

    s.append(_p("6.4 Volatility dampening", "h2"))
    s.extend(_ps([
        "To prevent projection churn from single-session noise, new values "
        "are blended with prior state using an adaptive alpha parameter. "
        "The alpha is clipped to [0.3, 0.7] to ensure the system remains "
        "responsive to real changes while filtering high-frequency noise. "
        "A large baseline shift (>5% vs previous) bypasses dampening entirely "
        "to avoid stale inertia masking genuine structural events:",
    ]))
    s.append(_eq("projected = alpha * raw + (1 - alpha) * previous", 29))
    s.append(Spacer(1, 2))
    s.append(_eq("alpha in [0.3, 0.7];  bypass if baseline shift > 5%", 30))
    s.append(Spacer(1, 2))
    s.append(_eq("volatility = abs(raw_projected - previous_projected)", 31))
    s.append(Spacer(1, 3))

    s.append(_p("6.5 Supported range", "h2"))
    s.extend(_ps([
        "The supported range communicates confidence context rather than "
        "expected race-day variance alone. It is the sum of four additive "
        "terms, each targeting a distinct source of uncertainty:",
    ]))
    s.append(_eq("base_pct = 0.015", 32))
    s.append(Spacer(1, 2))
    s.append(_eq("vol_pct = min(volatility / projected, 0.05)", 33))
    s.append(Spacer(1, 2))
    s.append(_eq("data_qual = available_features / total_features", 34))
    s.append(Spacer(1, 2))
    s.append(_eq("unc_pct = (1 - data_qual) * 0.02", 35))
    s.append(Spacer(1, 2))
    s.append(_eq("acwr_pct = 0.01 if acwr_4w > 1.5 or acwr_4w < 0.6", 36))
    s.append(Spacer(1, 2))
    s.append(_eq("total_pct = base + vol + unc + acwr", 37))
    s.append(Spacer(1, 2))
    s.append(_eq("range_low = projected * (1 - total_pct)", 38))
    s.append(Spacer(1, 2))
    s.append(_eq("range_high = projected * (1 + total_pct)", 39))
    s.append(Spacer(1, 3))
    s.append(_fig_uncertainty())
    s.append(_p(
        "Figure 2. Supported range composition from base uncertainty, "
        "volatility, data quality, and ACWR instability terms.",
        "caption"))

    s.append(_p("6.6 Driver decomposition", "h2"))
    s.extend(_ps([
        "Each driver's contribution to the total improvement is computed "
        "proportionally and constrained to sum exactly to the total. "
        "The final driver receives the arithmetic remainder after rounding, "
        "preserving closure:",
    ]))
    s.append(_eq("fraction_d = (score_d * weight_d) / sum(score * weight)", 40))
    s.append(Spacer(1, 2))
    s.append(_eq("contribution_d = round(fraction_d * total_improvement, 2)", 41))
    s.append(Spacer(1, 2))
    s.append(_eq("final_driver = total_improvement - sum(other contributions)", 42))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "When all weighted driver scores are zero but total improvement "
        "is nonzero, contributions are distributed evenly across the five "
        "drivers to preserve the sum constraint. This edge case arises "
        "when features are absent but the dampened projection carries "
        "forward a nonzero improvement from prior state.",
    ]))

    s.append(_p("6.7 Structural shift threshold", "h2"))
    s.extend(_ps([
        "User-visible projection updates require an absolute shift of at "
        "least 2.0 seconds. This threshold prevents UI churn from small "
        "numerical changes that carry no meaningful training interpretation. "
        "Below this threshold, the projection state is updated internally "
        "but not surfaced to the user.",

        "The 2-second threshold was chosen because it approximates the "
        "minimum change that a recreational runner would perceive as "
        "meaningful over a 5K distance. Smaller shifts are within normal "
        "session-to-session variation and would create a perception of "
        "instability if presented on every sync.",
    ]))

    s.append(_p("6.8 Design rationale", "h2"))
    s.extend(_ps([
        "The projection engine's design reflects a specific stance: it is "
        "better to be approximately right and explainable than precisely "
        "wrong and opaque. The weighted driver model is simple enough that "
        "a user can understand <i>why</i> their projection changed by "
        "examining which drivers moved and by how much.",

        "The 25% improvement cap is conservative by design. A runner "
        "improving from a 25:00 5K baseline can show at most a 6:15 "
        "improvement (to 18:45), which represents roughly the gap between "
        "a beginner and an intermediate competitive runner. The cap prevents "
        "the system from claiming a novice can project elite times based "
        "solely on a few weeks of structured training.",

        "Volatility dampening addresses a known failure mode in streaming "
        "prediction systems: when new data arrives frequently (multiple "
        "syncs per week), raw projections can oscillate between sessions. "
        "Dampening smooths this while the alpha bounds ensure the system "
        "never becomes completely unresponsive to genuine changes.",

        "The supported range is the most underappreciated component. "
        "Single-point estimates invite false precision; ranges communicate "
        "that the projection is conditional on data quality, training "
        "consistency, and load stability. The additive structure allows "
        "users to see <i>why</i> their range is wide (sparse data, high "
        "volatility, ACWR instability) and take action to narrow it.",
    ]))
    s.append(_p("6.9 Per-user Gradient Boosting projection", "h2"))
    s.extend(_ps([
        "When sufficient training history exists (minimum 30 activities), "
        "a per-user GradientBoostingRegressor is trained on the runner's "
        "own activity-to-improvement mapping. The model uses Huber loss "
        "for robustness to GPS-derived pace outliers and per-user training "
        "to capture individual response patterns that fixed driver weights "
        "cannot represent.",
    ]))
    s.append(_tbl(
        [
            ["Parameter", "Value", "Rationale"],
            ["loss", "huber", "Robust to pace outliers"],
            ["n_estimators", "200", "Sufficient ensemble depth"],
            ["max_depth", "4", "Limits overfitting on small user histories"],
            ["learning_rate", "0.008", "Slow shrinkage for better generalization"],
            ["subsample", "0.8", "Stochastic regularization"],
            ["MIN_TRAINING_SAMPLES", "30", "Statistical minimum for per-user fit"],
            ["recency_decay", "0.98", "Recent activities weighted higher"],
        ],
        [0.30 * TBL_W, 0.18 * TBL_W, 0.52 * TBL_W],
        "Table 5b. Gradient Boosting hyperparameters and constants."
    ))
    s.extend(_ps([
        "Sample weights follow an exponential recency decay that "
        "emphasizes recent training sessions while retaining earlier "
        "structural context:",
    ]))
    s.append(_eq("w_i = 0.98^(n-1-i),  normalized to sum = n", 43))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "The model accepts the same 17 features used in driver scoring "
        "and is trained on user activity history with targets computed as "
        "improvement delta relative to baseline, with Riegel scaling for "
        "non-5K distances. A reference_date is derived from each activity's "
        "timestamp for temporal alignment, preventing future data from "
        "leaking into training samples.",

        "Model quality is assessed via 5-fold weighted cross-validation "
        "using scikit-learn's cross_validate with sample weights passed "
        "through the params argument. The GB model overrides the "
        "deterministic driver-weighted projection when trained and active "
        "in the model registry.",
    ]))

    s.append(_p("6.10 LSTM temporal projection", "h2"))
    s.extend(_ps([
        "For temporal modeling of training adaptation dynamics, a per-user "
        "LSTM network captures sequential dependencies in feature snapshots "
        "that cross-sectional feature vectors cannot represent. The "
        "architecture processes sliding windows of consecutive feature "
        "observations to predict improvement trajectory.",
    ]))
    s.append(_tbl(
        [
            ["Parameter", "Value"],
            ["Architecture", "LSTM(17, 17, 1) -> Dropout(0.5) -> Linear(17, 1)"],
            ["Loss function", "HuberLoss"],
            ["Optimizer", "Adam, gradient clipping max_norm=1.0"],
            ["Sequence length", "11 feature snapshots"],
            ["Training split", "80/20 train/validation"],
            ["Early stopping", "patience=10 epochs"],
            ["Max epochs", "100"],
            ["Minimum samples", "120 activities (effective, after window offset)"],
        ],
        [0.30 * TBL_W, 0.70 * TBL_W],
        "Table 5c. LSTM architecture and training parameters."
    ))
    s.extend(_ps([
        "Inference uses the full temporal sequence from stored feature "
        "snapshots rather than a single-timestep input. The LSTM output "
        "is blended with the previous projection state to provide "
        "prediction continuity:",
    ]))
    s.append(_eq("predicted = 0.6 * lstm_output + 0.4 * previous_state", 44))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "The blend ratio reflects a design choice: the LSTM should "
        "influence but not dominate the projection, preserving stability "
        "during early deployment. The LSTM serving path is rollout-gated "
        "and requires all orchestrator checks to pass before overriding "
        "the deterministic or GB projection.",
    ]))

    s.append(_hr())
    return s


def _sec_constants():
    s = []
    s.append(_p("6.11 Constants and guardrails", "h2"))
    s.append(_tbl(
        [
            ["Constant", "Value", "Behavior controlled"],
            ["Structural shift threshold", "2.0 s", "Minimum change for user-visible update"],
            ["Max improvement cap", "25% of baseline", "Bounds optimism and prevents overfit drift"],
            ["Dampening alpha bounds", "[0.3, 0.7]", "Balances responsiveness and inertia"],
            ["Range base pct", "1.5%", "Default uncertainty floor"],
            ["Volatility cap", "min(vol/proj, 0.05)", "Prevents runaway range expansion"],
            ["Data quality penalty", "(1-qual)*0.02", "Penalizes sparse feature coverage"],
            ["ACWR range addition", "+1% outside [0.6, 1.5]", "Flags load-balance instability"],
            ["Feature score clip", "[0, 100]", "Prevents single-feature domination"],
            ["Minimum projected time", "60 s", "Avoids physiologically invalid outputs"],
            ["Baseline shift bypass", "> 5%", "Skips dampening on large events"],
        ],
        [0.32 * TBL_W, 0.22 * TBL_W, 0.46 * TBL_W],
        "Table 6. Projection constants and the failure modes each prevents."
    ))
    s.append(_hr())
    return s


def _sec_scaling():
    s = []
    s.append(_p("7. Event Scaling", "h1"))
    s.extend(_ps([
        "Cross-distance projection uses the Riegel power-law model [1], "
        "which relates performance across distances through a fatigue "
        "exponent. PIRX extends the base model with volume-adjusted "
        "exponents, individual fitting, phase-transition handling, and "
        "environmental adjustment.",
    ]))
    s.append(_p("7.1 Core Riegel formula", "h2"))
    s.append(_eq("T2 = T1 * (D2 / D1) ^ k", 45))
    s.append(Spacer(1, 2))
    s.append(_eq("default k = 1.06;  bounds [1.01, 1.15]", 46))
    s.append(Spacer(1, 3))

    s.append(_p("7.2 Volume-adjusted exponent", "h2"))
    s.extend(_ps([
        "Higher training volume improves endurance transfer, which is "
        "reflected in a lower fatigue exponent. The adjustment reduces k "
        "linearly above 40 km/week and clamps to prevent implausible values:",
    ]))
    s.append(_eq("k = max(0.98, 1.06 - 0.005*((weekly_km - 40)/10))", 47))
    s.append(Spacer(1, 2))
    s.append(_eq("k = min(k, 1.15)", 48))
    s.append(Spacer(1, 3))

    s.append(_p("7.3 Individual exponent fit", "h2"))
    s.extend(_ps([
        "When a runner has results at multiple distances, an individualized "
        "exponent is fit by least-squares regression in log space, then "
        "clamped to the physiologically plausible range:",
    ]))
    s.append(_eq("log(time) = k * log(distance) + b   [least squares]", 49))
    s.append(Spacer(1, 2))
    s.append(_eq("k_individual = clamp(k_fit, 1.01, 1.15)", 50))
    s.append(Spacer(1, 3))

    s.append(_p("7.4 Phase transition at 5K", "h2"))
    s.extend(_ps([
        "Crossing the 5K boundary introduces asymmetry in fatigue behavior. "
        "Scaling to longer distances adds +0.02 to the exponent; scaling to "
        "shorter distances subtracts 0.02. This captures the empirical "
        "observation that aerobic-to-anaerobic transfer is not symmetric:",
    ]))
    s.append(_eq("if D2 > 5000 and D1 <= 5000: k += 0.02", 51))
    s.append(Spacer(1, 2))
    s.append(_eq("if D2 < 5000 and D1 >= 5000: k -= 0.02", 52))
    s.append(Spacer(1, 3))

    s.append(_p("7.5 Environmental adjustment", "h2"))
    s.extend(_ps([
        "Performance degrades outside the optimal temperature range of "
        "10-17.5 C. The penalty is linear in degrees outside the band, "
        "based on meta-analytic estimates of heat/cold impact on endurance "
        "running [3]:",
    ]))
    s.append(_eq("multiplier = 1 + 0.0035 * degrees_outside_band", 53))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "The 0.35% per degree coefficient is conservative relative to "
        "some study estimates (which range 0.3-0.5%) and applies "
        "symmetrically to heat and cold. A 30 C race day for a runner "
        "with 22:00 base projection would add approximately 12.5 degrees "
        "outside band, yielding a ~4.4% time penalty (~58 seconds).",
    ]))

    s.append(_p("7.6 Scaling design rationale", "h2"))
    s.extend(_ps([
        "Riegel's power-law model was chosen over more complex alternatives "
        "(neural network regressors, Gaussian process models) because it "
        "has three properties critical for PIRX: (1) a single interpretable "
        "parameter (the exponent k); (2) established population baselines "
        "from decades of research [1]; and (3) the ability to incorporate "
        "individual variation through per-runner exponent fitting.",

        "The volume-adjusted exponent captures a well-documented training "
        "effect: higher-mileage runners exhibit better endurance transfer "
        "across distances. A 100 km/week runner loses less performance "
        "scaling from 5K to marathon than a 30 km/week runner. The "
        "adjustment formula quantifies this relationship while clamping "
        "to prevent extrapolation beyond observed ranges.",

        "The 5K boundary adjustment addresses the transition between "
        "predominantly aerobic (distances above 5K) and mixed "
        "aerobic-anaerobic (distances at or below 5K) energy systems. "
        "Without this adjustment, scaling from 5K to 10K would use the "
        "same exponent as scaling from 1500m to 3000m, which does not "
        "reflect the physiological shift in energy contribution.",
    ]))
    s.append(_hr())
    return s


def _sec_readiness():
    s = []
    s.append(_p("8. Readiness and Injury Risk", "h1"))
    s.extend(_ps([
        "Readiness is deliberately separated from projection capability. "
        "A runner can have a strong projected time but poor readiness "
        "(e.g., high ACWR from a recent load spike). This separation "
        "prevents conflating what training supports with whether the "
        "runner should race now.",
    ]))

    s.append(_p("8.1 Readiness score", "h2"))
    s.append(_eq("R = 0.30*acwr_bal + 0.25*fresh + 0.20*recency "
                  "+ 0.15*physio + 0.10*consist", 54))
    s.append(Spacer(1, 2))
    s.append(_eq("R_final = clip(R, 0, 100)", 55))
    s.append(Spacer(1, 3))

    s.append(_p("ACWR balance component:", "h2"))
    s.extend(_ps([
        "The optimal ACWR zone is [0.8, 1.3], centered at 1.05. Scores "
        "degrade progressively outside this window, with steeper penalties "
        "above 1.3 (overreaching) than below 0.8 (detraining):",
    ]))
    s.append(_eq("if 0.8 <= acwr <= 1.3:  100 - (|acwr-1.05|/0.25)*15", 56))
    s.append(Spacer(1, 2))
    s.append(_eq("if acwr > 1.3:  max(0, 85 - (acwr-1.3)*150)", 57))
    s.append(Spacer(1, 2))
    s.append(_eq("if acwr < 0.8:  max(0, 85 - (0.8-acwr)*100)", 58))
    s.append(Spacer(1, 3))

    s.append(_p("Freshness component:", "h2"))
    s.append(_tbl(
        [
            ["Days since activity", "Base score", "Race penalty (if recent)"],
            ["0", "55", "< 3 days: * 0.5"],
            ["1", "85", "< 7 days: * 0.7"],
            ["2", "90", "< 14 days: * 0.85"],
            ["3", "80", ""],
            ["4-5", "70", ""],
            ["6-10", "50", ""],
            ["> 10", "30", ""],
        ],
        [0.28 * TBL_W, 0.26 * TBL_W, 0.46 * TBL_W],
        "Table 7. Freshness component scoring with race-proximity penalty."
    ))

    s.append(_p("Training recency component:", "h2"))
    s.append(_eq("threshold_score = max(0, 100 - 5*days_since_threshold)", 59))
    s.append(Spacer(1, 2))
    s.append(_eq("long_run_score = max(0, 100 - 3*days_since_long_run)", 60))
    s.append(Spacer(1, 2))
    s.append(_eq("recency = 0.6*threshold_score + 0.4*long_run_score", 61))
    s.append(Spacer(1, 3))

    s.append(_p("Physiological component:", "h2"))
    s.append(_tbl(
        [
            ["Signal", "Score buckets"],
            ["Resting HR trend", "<= -1: 90 | <= 0: 70 | <= 2: 50 | else: 30"],
            ["HRV trend", ">= 2: 90 | >= 0: 70 | >= -2: 50 | else: 30"],
            ["Sleep score", "Direct value when available"],
        ],
        [0.27 * TBL_W, 0.73 * TBL_W],
        "Table 8. Physiological component scoring buckets."
    ))

    s.append(_p("Consistency component:", "h2"))
    s.append(_tbl(
        [
            ["Metric", "Score buckets"],
            ["Weekly load stddev (m)", "< 3000: 90 | < 6000: 70 | < 10000: 50 | else: 30"],
            ["Session stability", "< 0.5: 90 | < 1.0: 70 | < 2.0: 50 | else: 30"],
        ],
        [0.27 * TBL_W, 0.73 * TBL_W],
        "Table 9. Consistency component scoring buckets."
    ))

    s.append(_p("8.1.1 Trained readiness classifier", "h2"))
    s.extend(_ps([
        "When sufficient race-day outcome data exists (minimum 5 race "
        "results), a trained GradientBoostingClassifier replaces the "
        "heuristic weighting. The classifier uses 9 features: ACWR, "
        "days since last activity, days since last threshold session, "
        "days since last long run, HRV trend, resting HR trend, sleep "
        "score, weekly load standard deviation, and session density "
        "stability. The heuristic scoring (Eq. 54-61) serves as the "
        "universal fallback when insufficient race outcomes are available.",
    ]))
    s.append(_tbl(
        [
            ["Parameter", "Value"],
            ["Model", "GradientBoostingClassifier (sklearn)"],
            ["n_estimators", "100"],
            ["max_depth", "3"],
            ["learning_rate", "0.05"],
            ["Minimum race outcomes", "5"],
            ["Input features", "9 (ACWR, recency, physiology, consistency)"],
        ],
        [0.30 * TBL_W, 0.70 * TBL_W],
        "Table 9b. Readiness classifier parameters."
    ))

    s.append(_p("8.2 Injury risk model", "h2"))
    s.extend(_ps([
        "Injury risk estimation uses a two-tier architecture. The "
        "TrainableInjuryRiskModel (tier 1) is a RandomForestRegressor "
        "trained on real proxy injury signals extracted from the runner's "
        "history. The baseline InjuryRiskModel (tier 2) uses an identical "
        "architecture but is trained on synthetic data derived from "
        "population-level injury patterns. Both produce a calibrated "
        "probability mapped to actionable bands. Injury risk is additive "
        "to readiness context and intentionally does not mutate projection "
        "state, avoiding conflation of capability estimation with risk "
        "advisory signals.",
    ]))
    s.append(_eq("risk_band: low (p < 0.35), moderate (p < 0.60), high", 62))
    s.append(Spacer(1, 2))
    s.append(_eq("readiness_injury = (1 - risk_probability) * 100", 63))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "<b>Proxy injury signal extraction.</b> Two signals serve as "
        "injury proxies when labeled injury data is unavailable. First, "
        "an extended rest period exceeding 14 days following an ACWR "
        "of 1.4 or higher produces a label proportional to the gap: "
        "label = min(1, gap_days / 30). Second, a performance drop "
        "exceeding 10% within a 4-week window produces a label of 0.7 "
        "or higher. These proxy signals approximate injury events from "
        "observable behavioral patterns without requiring self-reported "
        "injury labels.",

        "<b>Calibration.</b> Risk probabilities are calibrated using a "
        "continuous piecewise linear function that ensures no discontinuities "
        "at boundary points:",
    ]))
    s.append(_eq("cal(p) = 0.9p if p<0.2; p-0.02 if 0.2<=p<0.7; 0.9p+0.05 if p>=0.7", 64))
    s.append(Spacer(1, 3))
    s.append(_tbl(
        [
            ["Parameter", "Value"],
            ["Trainable model", "RandomForestRegressor on proxy signals"],
            ["Baseline model", "RandomForestRegressor on synthetic data"],
            ["MIN_INJURY_SIGNALS", "30 for trainable activation"],
            ["Input features (8)", "acwr_4w/6w/8w, load_stddev, session_stability, hrv/rhr trend, sleep"],
        ],
        [0.30 * TBL_W, 0.70 * TBL_W],
        "Table 9c. Injury risk model parameters."
    ))

    s.append(_p("8.3 Trajectory prediction", "h2"))
    s.extend(_ps([
        "Trajectory prediction uses DTW-based block matching when "
        "sufficient history exists, with heuristic scenario multipliers "
        "as a fallback. Training history is partitioned into 14-calendar-day "
        "blocks, each fingerprinted as a matrix of (distance_km, "
        "duration_min, avg_pace, avg_hr) per activity. Features are "
        "z-score normalized per column before comparison to eliminate "
        "scale bias between dimensions.",
    ]))
    s.append(_eq("block_dist = mean(dtw(zscore(a_col), zscore(b_col)) for col in features)", 65))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "DTW distance is computed independently per feature column using "
        "the dtaidistance library and averaged across dimensions. The "
        "top-k (k=3) most similar historical blocks are matched, and "
        "trajectory is predicted from their observed outcomes. This "
        "approach discovers patterns in individual training periodization "
        "that fixed multipliers cannot capture.",

        "When insufficient block history exists (fewer than 4 blocks), "
        "heuristic scenario multipliers serve as fallback:",
    ]))
    s.append(_tbl(
        [
            ["Scenario", "Volume", "Intensity", "Consistency", "Confidence"],
            ["Maintain", "1.00", "1.00", "1.00", "0.85"],
            ["Push", "1.05", "1.15", "0.95", "0.65"],
            ["Ease off", "0.80", "0.90", "1.10", "0.75"],
        ],
        [0.22 * TBL_W, 0.18 * TBL_W, 0.20 * TBL_W, 0.22 * TBL_W, 0.18 * TBL_W],
        "Table 10. Heuristic trajectory scenario multipliers (DTW fallback)."
    ))
    s.extend(_ps([
        "Scenario delta is computed as the difference between current "
        "and hypothetical projected times after applying the feature "
        "transforms: delta = current_projected - scenario_projected.",
    ]))

    s.append(_p("8.4 Readiness design rationale", "h2"))
    s.extend(_ps([
        "The five-component readiness model was designed to capture "
        "distinct aspects of race-preparedness that runners intuitively "
        "reason about: load balance (am I overtraining?), recovery "
        "(am I fresh enough?), specificity (have I done key workouts "
        "recently?), physiological state (how does my body feel?), and "
        "consistency (have I been training regularly?).",

        "Each component answers a different coaching question, and the "
        "weighted combination produces a single score that can be "
        "decomposed for explanation. The weights prioritize ACWR balance "
        "(0.30) and freshness (0.25) because these are the most volatile "
        "and the most likely to signal immediate risk. Consistency (0.10) "
        "has the lowest weight because it changes slowly and rarely "
        "drives acute readiness shifts.",

        "Readiness labels (Peak, Good, Moderate, Low, Very Low) are "
        "intentionally simple. The goal is actionable interpretation, "
        "not statistical nuance. A runner seeing 'Low' readiness should "
        "understand that racing is inadvisable without needing to decode "
        "a numerical score. The labels map to score ranges that were "
        "calibrated against coaching consensus for recreational and "
        "competitive club runners.",

        "The explicit separation of injury risk from readiness prevents "
        "a common product failure: conflating how prepared you are with "
        "how likely you are to get hurt. These are correlated but distinct "
        "concepts. A well-trained runner who recently spiked volume may "
        "have high readiness (fresh and fit) but elevated injury risk "
        "(acute load spike). PIRX surfaces both signals independently.",
    ]))
    s.append(_hr())
    return s


def _sec_orchestration():
    s = []
    s.append(_p("9. Model Orchestration and Rollout", "h1"))
    s.extend(_ps([
        "PIRX uses a centralized ModelOrchestrator that governs which "
        "computation path produces the projection output. The orchestrator "
        "selects from three paths: (1) deterministic (default and "
        "reliability floor), (2) per-user Gradient Boosting model (when "
        "trained and active in the model registry), and (3) LSTM temporal "
        "model (rollout-gated). ML-based serving is introduced only "
        "through explicit gates:",
    ]))
    s.append(_p("&#8226; Feature flag: <font face='Courier' size='7'>enable_lstm_serving</font> must be true.", "bullet"))
    s.append(_p("&#8226; Cohort gate: <font face='Courier' size='7'>user_hash % 100 &lt; rollout_pct</font>.", "bullet"))
    s.append(_p("&#8226; Artifact check: active model must have a retrievable artifact.", "bullet"))
    s.append(_p("&#8226; GB model: active GB model loaded from model_registry; predictions override deterministic when available.", "bullet"))
    s.append(_p("&#8226; Fallback: if any check fails, deterministic path is used and fallback_reason is recorded.", "bullet"))
    s.append(Spacer(1, 4))
    s.append(_fig_orchestrator())
    s.append(_p(
        "Figure 3. Model serving topology with deterministic default, "
        "GB per-user path, gated LSTM path, and explicit fallback.",
        "caption"))

    s.append(_p("9.1 ML lifecycle and hyperparameter optimization", "h2"))
    s.extend(_ps([
        "Training and tuning jobs persist auditable records across five "
        "lifecycle tables: model_registry, model_training_jobs, "
        "optuna_studies, optuna_trials, and model_artifacts. Promotion "
        "from tuning to active serving requires the best trial value to "
        "meet a quality threshold (best_value &lt;= 0.34), and superseded "
        "models are explicitly deactivated.",

        "LSTM hyperparameter optimization uses Optuna with per-user "
        "studies. Each study minimizes validation loss over a structured "
        "search space:",
    ]))
    s.append(_tbl(
        [
            ["Hyperparameter", "Search space"],
            ["hidden_dim", "[8, 64] (integer)"],
            ["dropout", "[0.1, 0.6] (continuous)"],
            ["learning_rate", "[1e-4, 1e-2] (log-uniform)"],
            ["batch_size", "{16, 32, 56} (categorical)"],
        ],
        [0.35 * TBL_W, 0.65 * TBL_W],
        "Table 11a. Optuna LSTM hyperparameter search space."
    ))
    s.extend(_ps([
        "The trial budget scales with data availability: n_trials = "
        "min(20, max(5, n_samples / 10)), with a 300-second timeout. "
        "Complete trial histories including hyperparameters, objective "
        "values, and study-level summaries are persisted to optuna_studies "
        "and optuna_trials tables for auditability. Promotion threshold "
        "of best_value &lt;= 0.34 ensures only validated candidates enter "
        "the serving path.",
    ]))

    s.append(_p("9.2 Rollout endpoints", "h2"))
    s.append(_tbl(
        [
            ["Endpoint", "Purpose"],
            ["/rollout/config", "Current flag and percentage state"],
            ["/rollout/metrics?days=N", "Serving-decision aggregation by event/model"],
            ["/rollout/release-readiness", "Gate status + metric summary for go/no-go"],
        ],
        [0.40 * TBL_W, 0.60 * TBL_W],
        "Table 11. Operational rollout endpoints."
    ))
    s.append(_p("9.3 Serving-decision observability", "h2"))
    s.extend(_ps([
        "Every projection recompute writes a model_serving_decision metric "
        "to model_metrics, recording which branch was selected, whether "
        "fallback was triggered, and the event context. This creates an "
        "audit trail that supports three operational workflows: (1) "
        "confirming that rollout percentages are producing expected cohort "
        "ratios; (2) detecting elevated fallback rates that indicate model "
        "health issues; and (3) computing release-readiness scores that "
        "combine gate state with live serving metrics.",

        "The release-readiness endpoint aggregates these metrics with "
        "gate state to produce a structured go/no-go summary. Operators "
        "can verify that all prerequisites are met before increasing "
        "rollout percentage, without needing to query the database "
        "directly or interpret raw metric rows.",
    ]))
    s.append(_p("9.4 Promotion guardrails", "h2"))
    s.extend(_ps([
        "Optuna tuning jobs persist complete trial histories, including "
        "hyperparameters, objective values, and study-level summaries. "
        "Promotion to active serving requires the best trial value to "
        "meet a quality threshold (best_value <= 0.34). Models that do "
        "not meet this threshold are marked inactive, ensuring that only "
        "validated candidates enter the serving path.",

        "When a new model is promoted, previously active models for the "
        "same user/event are explicitly deactivated. This prevents "
        "ambiguity about which model is serving and ensures that the "
        "orchestrator always resolves to a single active candidate.",
    ]))
    s.append(_hr())
    return s


def _sec_operational():
    s = []
    s.append(_p("10. Operational Safeguards", "h1"))

    s.append(_p("10.1 Inactivity decay", "h2"))
    s.extend(_ps([
        "When no valid activities are recorded for extended periods, "
        "projection confidence degrades systematically rather than "
        "remaining stale:",
    ]))
    s.append(_eq("if inactive > 10d: range widens 5% each side, "
                  "conf -= 0.05 (floor 0.1)", 66))
    s.append(Spacer(1, 2))
    s.append(_eq("if inactive > 21d: status -> Declining, "
                  "conf -= 0.10 (floor 0.1)", 67))
    s.append(Spacer(1, 3))

    s.append(_p("10.2 Confidence score", "h2"))
    s.append(_eq("confidence = max(0, 1 - volatility / projected)", 68))
    s.append(Spacer(1, 3))

    s.append(_p("10.3 Accuracy monitoring", "h2"))
    s.extend(_ps([
        "Post-race accuracy is assessed using mean absolute error, "
        "directional bias, and Bland-Altman agreement bounds. These "
        "metrics inform both system-level calibration and per-user "
        "bias-correction logic:",
    ]))
    s.append(_eq("MAE = mean(|actual - projected|)", 69))
    s.append(Spacer(1, 2))
    s.append(_eq("bias = mean(actual - projected)", 70))
    s.append(Spacer(1, 2))
    s.append(_eq("Bland-Altman: bias +/- 1.96 * std(biases)", 71))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "When per-race bias exceeds 10 seconds, a metric is logged for "
        "monitoring. Systematic bias accumulation triggers investigation "
        "into baseline calibration or feature computation drift.",
    ]))
    s.append(_p("10.4 Bias correction", "h2"))
    s.extend(_ps([
        "The bias correction task compares the latest race result against "
        "the projection for the corresponding event distance. When the "
        "absolute bias exceeds 10 seconds, a metric row is persisted "
        "with the bias magnitude and direction. This threshold prevents "
        "noise from minor timing differences while ensuring that "
        "systematic over- or under-prediction is detected.",

        "Bland-Altman bounds provide a population-level view of "
        "agreement. When the 95% limits of agreement (mean +/- 1.96 SD) "
        "exceed acceptable thresholds, this signals that the projection "
        "engine may need recalibration or that specific user segments "
        "are experiencing systematic bias.",
    ]))
    s.append(_p("10.5 Task scheduling", "h2"))
    s.extend(_ps([
        "Background tasks are coordinated through Celery with three "
        "queue types: the default queue for sync and feature tasks, "
        "the ml queue for training and tuning lifecycle jobs, and "
        "scheduled beats for periodic maintenance (inactivity decay, "
        "weekly training/tuning). Task deduplication uses 300-second "
        "lock windows to prevent redundant computation when multiple "
        "sync events arrive in rapid succession.",
    ]))
    s.append(_hr())
    return s


def _sec_validation():
    s = []
    s.append(_p("10.6 Validation methodology", "h2"))
    s.extend(_ps([
        "Validation in PIRX operates at three levels: formula-level "
        "verification, integration-level testing, and production-level "
        "monitoring. Each level targets different failure modes and "
        "operates on different timescales.",
    ]))
    s.append(_p("Formula-level verification:", "h2"))
    s.extend(_ps([
        "Unit tests verify that each equation produces expected outputs "
        "for known inputs. These tests cover boundary conditions (zero "
        "features, all features at 100, edge-case ACWR values), "
        "numerical stability (very large or small inputs), and "
        "constraint satisfaction (driver contributions sum to total "
        "improvement, range_low < projected < range_high).",

        "The projection engine has dedicated tests for dampening "
        "behavior (verifying alpha bounds are respected), baseline "
        "shift bypass (confirming dampening is skipped for large shifts), "
        "and structural shift gating (confirming that sub-threshold "
        "changes are suppressed). These tests run on every commit and "
        "provide regression protection.",
    ]))
    s.append(_p("Integration-level testing:", "h2"))
    s.extend(_ps([
        "Integration tests verify that the pipeline stages compose "
        "correctly. A sync event should trigger cleaning, then feature "
        "recompute, then projection update, with the final projection "
        "reflecting the new data. These tests use mock data that "
        "exercises specific scenarios: new user with no history, "
        "returning user with stale data, user with recent race result.",

        "The model orchestrator has specific integration tests for "
        "each serving branch: deterministic-only (flag disabled), "
        "deterministic fallback (flag enabled but artifact missing), "
        "and LSTM override (flag enabled with valid artifact). Each "
        "test verifies that the correct metadata (model_source, "
        "fallback_reason) is persisted with the projection row.",
    ]))
    s.append(_p("Production-level monitoring:", "h2"))
    s.extend(_ps([
        "In production, accuracy_tasks compute MAE and bias metrics "
        "whenever a race result matches a projected event. These metrics "
        "are persisted to model_metrics with event context, enabling "
        "per-distance accuracy tracking. The rollout endpoints aggregate "
        "these metrics for operational dashboards.",

        "Serving-decision metrics track the distribution of model "
        "branches selected over time. A sudden increase in fallback "
        "rates signals model health issues (artifact corruption, "
        "registry inconsistency). Conversely, stable serving ratios "
        "matching the configured rollout percentage confirm that "
        "cohort gating is functioning correctly.",

        "The validation strategy is intentionally layered. No single "
        "level catches all failure modes. Formula tests catch regression "
        "bugs; integration tests catch composition errors; production "
        "monitoring catches drift and environmental issues that only "
        "manifest with real user data.",
    ]))
    s.append(_tbl(
        [
            ["Level", "Scope", "Failure modes caught", "Frequency"],
            ["Formula", "Single equation", "Regression, boundary errors", "Every commit"],
            ["Integration", "Pipeline stage composition", "Wiring, state propagation", "Every commit"],
            ["Production", "Real user accuracy + serving", "Drift, calibration, env issues", "Continuous"],
        ],
        [0.18 * TBL_W, 0.26 * TBL_W, 0.34 * TBL_W, 0.22 * TBL_W],
        "Table 11b. Three-level validation strategy."
    ))
    s.append(_hr())
    return s


def _sec_api_calcs():
    s = []
    s.append(_p("11. API-Level Derived Calculations", "h1"))
    s.extend(_ps([
        "Several calculations occur at the API or service layer rather "
        "than in the core ML modules. While not primary model equations, "
        "they materially affect user-facing outputs and must be documented "
        "for auditability.",
    ]))
    s.append(_p("11.1 Driver persistence", "h2"))
    s.append(_eq("21d_change = midpoint_21d_ago - current_projected", 72))
    s.append(Spacer(1, 2))
    s.append(_eq("confidence = max(0, 1 - volatility / projected)", 73))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "Driver stability is classified from the last 6 driver scores "
        "using standard deviation and net trend (last minus first). High "
        "stddev indicates oscillation; net trend indicates directional "
        "change. These classifications appear in the frontend driver "
        "history views.",
    ]))
    s.append(_p("11.2 Projection API fallbacks", "h2"))
    s.extend(_ps([
        "The API layer applies defensive defaults when optional fields "
        "are absent. These fallbacks ensure the frontend always receives "
        "a complete response shape, even for older projection rows that "
        "predate schema additions:",
    ]))
    s.append(_eq("if range missing: low = mid*0.97, high = mid*1.03", 74))
    s.append(Spacer(1, 2))
    s.append(_eq("if baseline missing: fallback = midpoint + 78", 75))
    s.append(Spacer(1, 2))
    s.append(_eq("improvement = baseline - midpoint", 76))
    s.append(Spacer(1, 3))

    s.append(_p("11.3 Zone methodology", "h2"))
    s.extend(_ps([
        "Training intensity distribution is classified from heart-rate "
        "zone proportions using a decision tree that distinguishes four "
        "common training philosophies:",
    ]))
    s.append(_eq("low_intensity = z1_pct + z2_pct", 77))
    s.append(Spacer(1, 2))
    s.append(_eq("high_intensity = z4_pct + z5_pct", 78))
    s.append(Spacer(1, 2))
    s.append(_eq("z3_pct = zone3_time / total_zone_time", 79))
    s.append(Spacer(1, 3))
    s.append(_tbl(
        [
            ["Condition", "Classification"],
            ["low_intensity > 0.75 and z3_pct < 0.05", "Polarized"],
            ["low_intensity > 0.75", "Pyramidal"],
            ["high_intensity > 0.20", "Threshold-heavy"],
            ["Otherwise", "Mixed"],
        ],
        [0.62 * TBL_W, 0.38 * TBL_W],
        "Table 12. Training intensity classification rules."
    ))
    s.extend(_ps([
        "The distinction between Polarized and Pyramidal training requires "
        "examining the Zone 3 (threshold) percentage. Both exhibit high "
        "low-intensity volume, but Polarized training is defined by minimal "
        "time in the moderate-intensity zone (z3 &lt; 5%), reflecting the "
        "classic two-peak distribution documented in elite training studies.",
    ]))
    s.extend(_ps([
        "When HR zone data is unavailable, a fallback classifier uses HR "
        "percentage of estimated maximum (190 bpm default): easy (<70%), "
        "moderate (70-85%), hard (>=85%), with zone splits of "
        "z1=40%/z2=60% for easy, z3=50%/z4=50% for moderate, and z5=hard.",
    ]))
    s.append(_p("11.4 Running economy endpoint", "h2"))
    s.extend(_ps([
        "Economy is assessed by comparing matched-HR band pace across "
        "windowed periods. The current window (21 days) is compared "
        "against the prior baseline window (days 22-42) to detect "
        "efficiency changes that are independent of effort variation:",
    ]))
    s.append(_eq("matched_band = sessions where 145 <= avg_hr <= 155", 80))
    s.append(Spacer(1, 2))
    s.append(_eq("hr_cost_change = ((curr_pace - base_pace) / base_pace) * 100", 81))
    s.append(Spacer(1, 2))
    s.append(_eq("economy_confidence = min(sessions_analyzed / 20, 1.0)", 82))
    s.append(Spacer(1, 3))
    s.append(_hr())
    return s


def _sec_pattern_detection():
    s = []
    s.append(_p("11.5 Pattern detection and training type classification", "h2"))
    s.extend(_ps([
        "The learning module applies unsupervised pattern detection to "
        "identify training structure and feature-to-driver response "
        "relationships. Two complementary approaches are employed: "
        "K-Means clustering for training type classification and "
        "correlation analysis for adaptive response detection.",
    ]))
    s.append(_p("K-Means clustering:", "h2"))
    s.extend(_ps([
        "Training intensity distributions (Z1-Z5 proportions) are "
        "clustered using K-Means with n_clusters = min(4, n_samples) "
        "and n_init = 10 for stability. Cluster centers are classified "
        "into training types using the rules from Table 12. This "
        "provides a data-driven classification that accounts for the "
        "runner's actual training distribution rather than relying on "
        "a single snapshot.",
    ]))
    s.append(_p("Correlation-based response detection:", "h2"))
    s.extend(_ps([
        "Pearson and Spearman correlation coefficients are computed "
        "between feature time series and driver score histories to "
        "detect statistically significant response patterns. Feature "
        "snapshots and driver history are paired using date-based keys "
        "for temporal alignment. Significant responses are identified "
        "when both conditions are met:",
    ]))
    s.append(_eq("significant if: p < 0.05 and |r| > 0.4", 83))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "A negative ACWR-performance correlation indicates a personal "
        "danger zone where load spikes reliably degrade the runner's "
        "driver scores. These patterns generate advisory signals consumed "
        "by the chat agent and learning insights views. Pattern detection "
        "does not modify projection state directly but enriches the "
        "interpretive context available to downstream consumers.",
    ]))
    s.append(_hr())
    return s


def _sec_discussion():
    s = []
    s.append(_p("12. Discussion", "h1"))
    s.extend(_ps([
        "A recurring failure mode in sports prediction systems is opacity: "
        "users cannot determine whether changes are physiologically "
        "meaningful or model noise. PIRX mitigates this through three "
        "mechanisms: structural shift thresholds that suppress presentation "
        "noise, range semantics that communicate confidence rather than false "
        "precision, and provenance metadata that discloses which model path "
        "produced each output.",

        "The deterministic-first design is a deliberate architectural choice, "
        "not a compromise. Users must trust that state changes are explainable "
        "before they trust that state changes are optimal. This principle "
        "drives the entire rollout architecture: ML components are gated, "
        "fallback is automatic, and every serving decision is recorded. "
        "Without this trust foundation, personalization improvements are "
        "wasted because users discount outputs they cannot interpret.",

        "From a coaching perspective, this architecture supports interpretation: "
        "users can connect projections to driver changes and training structure "
        "rather than treating outputs as unexplained scores. The driver "
        "decomposition constraint (contributions sum to total improvement) "
        "ensures that aggregate and component views remain consistent. When "
        "a coach asks 'why did the projection change?', the answer is always "
        "traceable to specific driver movements and the features that caused them.",

        "The approach has clear tradeoffs. While per-user Gradient Boosting "
        "and LSTM models now capture individual response variation, the "
        "deterministic equations with fixed weights remain the reliability "
        "floor. The ACWR formulation, while practical, simplifies complex "
        "dose-response dynamics into a ratio. The Riegel exponent, even "
        "with adjustments, assumes power-law scaling that breaks down at "
        "ultra distances. The layered architecture accepts these tradeoffs "
        "by using ML to personalize when data supports it, while preserving "
        "the deterministic path as a safe fallback.",

        "The separation of projection (capability) from readiness "
        "(race-preparedness) deserves emphasis. Most competing systems "
        "blend these into a single score, which obscures actionable insight. "
        "A runner with excellent aerobic fitness but dangerously high ACWR "
        "needs different advice than a runner with moderate fitness and "
        "well-balanced load. PIRX preserves this distinction because it "
        "changes the coaching conversation.",

        "Range semantics serve a similar purpose. Showing a supported "
        "range of 22:30-23:15 rather than a point estimate of 22:52 "
        "communicates that the projection has confidence context. The "
        "range widens under sparse data, high volatility, or ACWR "
        "instability, giving users a visual indicator of projection "
        "reliability without requiring them to understand uncertainty "
        "statistics.",

        "The rollout architecture deserves separate consideration. Many "
        "ML systems ship models by replacing the default path. PIRX treats "
        "model transitions as staged releases with observable, reversible "
        "controls. The deterministic engine never stops running; ML models "
        "override its output only when all gates pass. This means rollback "
        "is instantaneous (disable the flag) and serving-decision metrics "
        "accumulate continuously for release-readiness assessment.",
    ]))
    s.append(_hr())
    return s


def _sec_limitations():
    s = []
    s.append(_p("13. Limitations", "h1"))
    s.extend(_ps([
        "The LSTM serving path remains rollout-gated by design, meaning "
        "full temporal personalization is not yet the default for all users. "
        "Per-user Gradient Boosting models are active when trained, but "
        "users with fewer than 30 activities receive only deterministic "
        "projections. This is a deliberate safety choice that prioritizes "
        "validated personalization over universal ML coverage.",

        "Current figures are schematic (architecture-oriented) rather than "
        "empirical plots from held-out benchmark cohorts. Quantitative "
        "validation tables with error distributions should be added when "
        "shared benchmark protocols and sufficient race-outcome data are "
        "available for statistically meaningful comparisons.",

        "Wearable data quality varies by provider, device model, firmware "
        "version, and wearing pattern. Despite aggressive cleaning and "
        "outlier controls, upstream sensor noise remains an external "
        "constraint that bounds achievable accuracy. Heart-rate optical "
        "sensor accuracy degrades during high-intensity intervals, which "
        "can affect zone classification and efficiency features.",

        "The readiness score weights and threshold buckets use "
        "expert-calibrated defaults. The trained GradientBoostingClassifier "
        "replaces these when sufficient race outcomes exist, but the "
        "minimum threshold of 5 race results limits its reach to users "
        "with active racing histories.",

        "The driver weights are currently fixed across all users. While "
        "this provides predictable behavior, it cannot capture the known "
        "fact that aerobic base contributes differently to performance "
        "for a novice runner versus an elite marathoner. Personalized "
        "weight learning is a natural extension but requires careful "
        "bounds to prevent overfitting on limited individual data.",

        "ACWR, while widely used in load monitoring, has known limitations "
        "as a single-number summary of training load dynamics. The ratio "
        "cannot distinguish between increases from more volume versus "
        "more intensity, and edge cases at the start of training blocks "
        "(when chronic load is small) can produce unstable ratios. PIRX "
        "mitigates this with three window variants and EWMA smoothing, "
        "but the fundamental compression remains.",
    ]))
    s.append(_hr())
    return s


def _sec_future():
    s = []
    s.append(_p("14. Future Work", "h1"))
    s.extend(_ps([
        "Several directions for extending PIRX are supported by the "
        "current architecture without requiring fundamental redesign. "
        "Each area is described with its prerequisites and the safety "
        "constraints that must be preserved.",

        "<b>Personalized driver weights.</b> The current fixed weights "
        "(0.30/0.25/0.15/0.15/0.15) apply uniformly across all users. "
        "With sufficient race-outcome data per user, individual weight "
        "vectors could be learned through constrained optimization "
        "(weights must sum to 1.0, stay positive, and remain within "
        "plausible physiological ranges). The interpretability requirement "
        "is preserved because the driver structure remains; only the "
        "relative emphasis changes.",

        "<b>Population-level validation.</b> The accuracy monitoring "
        "infrastructure (MAE, bias, Bland-Altman) is in place but requires "
        "a statistically meaningful sample of race outcomes to produce "
        "reportable benchmarks. As race results accumulate, per-distance "
        "accuracy tables and calibration plots should be generated and "
        "included in future versions of this document.",

        "<b>Advanced load modeling.</b> ACWR captures load balance but "
        "compresses complex dose-response dynamics into a single ratio. "
        "More sophisticated approaches (training impulse decomposition, "
        "fitness-fatigue models) could improve readiness accuracy. The "
        "readiness engine's component structure supports adding new "
        "components without changing the weighted-sum architecture.",

        "<b>Pacing and taper integration.</b> The current projection "
        "estimates capability but does not model how taper or pacing "
        "strategy affects race-day realization of that capability. "
        "Future extensions could combine the trajectory engine's scenario "
        "simulation with evidence-based taper protocols to provide "
        "race-week-specific guidance.",

        "<b>Multi-sport extension.</b> The feature engineering and "
        "projection architecture is sport-agnostic at the equation level. "
        "Extension to cycling (power-based features) or triathlon "
        "(multi-discipline aggregation) would require new feature "
        "extractors and sport-specific cleaning rules but could reuse "
        "the driver, projection, and rollout infrastructure.",
    ]))
    s.append(_hr())
    return s


def _sec_conclusion():
    s = []
    s.append(_p("15. Conclusion", "h1"))
    s.extend(_ps([
        "PIRX combines transparent equation-based projection with controlled "
        "ML personalization. The system answers a specific question — what "
        "does training structurally support right now — using deterministic "
        "formulas that are bounded, dampened, and decomposable into named "
        "driver contributions.",

        "The key contribution is not only model choice but system design: "
        "data conditioning removes noise before it reaches model inputs; "
        "bounded state updates prevent unrealistic claims; explicit "
        "uncertainty communicates confidence context through supported "
        "ranges; and staged rollout governance ensures that ML "
        "personalization is introduced safely and reversibly.",

        "The 87 equations documented in this paper are not aspirational "
        "specifications; they are verified against the active codebase "
        "and labeled with implementation status (active, rollout-gated, "
        "non-primary). This labeling discipline is itself a contribution: "
        "it prevents documentation from implying capabilities that are "
        "not yet production-default.",

        "As rollout-gated modules mature, population-level validation "
        "data accumulates, and personalized driver weights become feasible, "
        "the system can increase personalization without sacrificing the "
        "interpretability and safety guarantees that define the "
        "projection-first architecture. The deterministic floor remains "
        "available as a fallback at every stage of that evolution.",
    ]))
    s.append(_hr())
    return s


def _sec_appendix_formulas():
    s = []
    s.append(_p("Appendix A. Complete Formula Catalog", "h1"))
    s.extend(_ps([
        "This appendix provides a compact reference of all numbered "
        "equations in the document. Equations are grouped by functional "
        "area and cross-referenced to the section where they are derived.",
    ]))
    s.append(_tbl(
        [
            ["#", "Area", "Equation"],
            ["1", "Feature weighting", "W = 0.45*W_7d + 0.35*W_8-21d + 0.20*W_22-90d"],
            ["2-4", "Volume", "rolling_dist_Nd = sum(dist, last N days)"],
            ["5-7", "Intensity", "zN_pct = zone_N/total; threshold/speed min/wk"],
            ["8-10", "Efficiency", "matched_hr_pace; hr_drift; pace_decay"],
            ["11-13", "Consistency", "load_stddev; block_var; session_stability"],
            ["14-17", "ACWR", "alpha; EWMA smoothing; EWMA seed; acute/chronic"],
            ["18", "Race detection", "hr_pct = avg_hr/max_hr >= 0.83"],
            ["19-22", "Driver score", "ratio -> clip(50*ratio, 0, 100) -> mean"],
            ["23", "ACWR U-shape", "clip(100*(1-min(|acwr-1.05|/0.5,1)),0,100)"],
            ["24", "Weighted sum", "sum(score_d * weight_d)"],
            ["25-28", "Improvement", "factor=(Sw-50)/50; cap=0.25*base; proj=max(b-imp,60)"],
            ["29-31", "Dampening", "alpha*raw + (1-a)*prev; bypass if shift>5%"],
            ["32-39", "Range", "base+vol+unc+acwr -> low/high"],
            ["40-42", "Driver decomp", "proportional fraction; final=remainder"],
            ["43", "GB sample weight", "w_i = 0.98^(n-1-i), normalized"],
            ["44", "LSTM blend", "pred = 0.6*lstm + 0.4*prev"],
            ["45-46", "Riegel core", "T2 = T1*(D2/D1)^k; k=1.06 default"],
            ["47-48", "Volume-adj k", "k = max(0.98, 1.06-0.005*((km-40)/10))"],
            ["49-50", "Individual fit", "log(t)=k*log(d)+b; clamp [1.01,1.15]"],
            ["51-52", "5K transition", "+/-0.02 on boundary crossing"],
            ["53", "Temperature", "mult = 1 + 0.0035 * degrees_outside"],
            ["54-55", "Readiness total", "weighted 5-component, clip [0,100]"],
            ["56-58", "ACWR balance", "piecewise: [0.8,1.3] optimal zone"],
            ["59-61", "Training recency", "threshold + long_run weighted decay"],
            ["62-63", "Injury risk", "band thresholds; readiness integration"],
            ["64", "Calibration", "piecewise linear: slopes 0.9/1.0/0.9"],
            ["65", "DTW block dist", "mean(dtw(zscore(col)) for features)"],
            ["66-67", "Inactivity", "widen 5% >10d; Declining >21d"],
            ["68", "Confidence", "max(0, 1 - vol/proj)"],
            ["69-71", "Accuracy", "MAE, bias, Bland-Altman bounds"],
            ["72-76", "API derivations", "21d_change, confidence, fallbacks"],
            ["77-79", "Zone classification", "low/high intensity; z3_pct"],
            ["80-82", "Economy", "matched_band; hr_cost_change; confidence"],
            ["83", "Correlation test", "significant if p<0.05 and |r|>0.4"],
            ["84-87", "LMC (non-primary)", "log-space completion with coeff bounds"],
        ],
        [0.12 * TBL_W, 0.24 * TBL_W, 0.64 * TBL_W],
        "Table A1. Complete equation catalog with 87 numbered equations."
    ))
    return s


def _sec_appendix_modules():
    s = []
    s.append(_p("Appendix A2. Module Responsibility Map", "h1"))
    s.extend(_ps([
        "Each module in the backend has a single primary responsibility "
        "and addresses a specific reliability risk. This mapping supports "
        "code review: when reviewing a change, verify that it stays "
        "within the module's stated responsibility boundary.",
    ]))
    s.append(_tbl(
        [
            ["Module", "Responsibility", "Risk addressed"],
            ["cleaning_service.py", "Activity admissibility", "Garbage-in drift"],
            ["feature_service.py", "Rolling features + ACWR", "Sparse/noisy vectors"],
            ["baseline_estimator.py", "Tiered 5K anchor", "Unstable baselines"],
            ["reference_population.py", "KNN cold-start", "Default-anchor overuse"],
            ["projection_engine.py", "Driver scoring + range", "Opaque projection jumps"],
            ["gb_projection_model.py", "Per-user GB projection", "Fixed-weight limitation"],
            ["lstm_model.py", "LSTM train + serialize", "Temporal blind spots"],
            ["event_scaling.py", "Cross-distance transfer", "Distance inconsistency"],
            ["readiness_engine.py", "Readiness + GBC classifier", "Oversimplification"],
            ["trajectory_engine.py", "DTW block + scenario", "Static-only interpretation"],
            ["workout_similarity.py", "DTW block comparison", "Unscaled similarity"],
            ["model_orchestrator.py", "Serving branch selection", "Unsafe model cutover"],
            ["lstm_inference.py", "Artifact-backed override", "Unbounded model injection"],
            ["injury_risk_model.py", "Two-tier risk model", "Projection/risk conflation"],
            ["learning_module.py", "KMeans + correlation", "Missing patterns"],
            ["shap_explainer.py", "TreeExplainer attribution", "Opaque driver narratives"],
            ["driver_service.py", "Contribution persistence", "Non-summing narratives"],
            ["projection_tasks.py", "Decay + backfill", "Stale projections"],
            ["accuracy_tasks.py", "Error/bias metrics", "Unmeasured drift"],
            ["ml_tasks.py", "Training + tuning lifecycle", "Untracked lineage"],
            ["rollout.py", "Gate + metrics visibility", "Low observability"],
        ],
        [0.34 * TBL_W, 0.32 * TBL_W, 0.34 * TBL_W],
        "Table A2. Module-level responsibility and risk mapping."
    ))
    return s


def _sec_appendix_status():
    s = []
    s.append(_p("Appendix B. Implementation Status Matrix", "h1"))
    s.append(_tbl(
        [
            ["Component", "Status", "Module path"],
            ["Deterministic projection", "Active", "ml/projection_engine.py"],
            ["GB Projection Model", "Active", "ml/gb_projection_model.py"],
            ["LSTM Training Pipeline", "Active", "ml/lstm_model.py"],
            ["Feature engineering", "Active", "services/feature_service.py"],
            ["Baseline estimator (tiered)", "Active", "ml/baseline_estimator.py"],
            ["KNN cold-start", "Active", "ml/reference_population.py"],
            ["Event scaling (Riegel)", "Active", "ml/event_scaling.py"],
            ["Readiness engine + GBC", "Active", "ml/readiness_engine.py"],
            ["Trainable Injury Risk (RF)", "Active", "ml/injury_risk_model.py"],
            ["Trajectory (DTW + heuristic)", "Active", "ml/trajectory_engine.py"],
            ["Workout Similarity (DTW)", "Active", "ml/workout_similarity.py"],
            ["Driver decomposition", "Active", "services/driver_service.py"],
            ["SHAP TreeExplainer", "Active", "ml/shap_explainer.py"],
            ["Learning module (KMeans)", "Active", "ml/learning_module.py"],
            ["Accuracy/bias monitoring", "Active", "tasks/accuracy_tasks.py"],
            ["Inactivity decay", "Active", "tasks/projection_tasks.py"],
            ["Model orchestrator", "Active", "services/model_orchestrator.py"],
            ["LSTM inference adapter", "Rollout-gated", "ml/lstm_inference.py"],
            ["Optuna tuning lifecycle", "Active", "tasks/ml_tasks.py"],
            ["Rollout APIs", "Active", "routers/rollout.py"],
            ["LMC module", "Non-primary", "ml/lmc.py"],
        ],
        [0.36 * TBL_W, 0.22 * TBL_W, 0.42 * TBL_W],
        "Table B1. Implementation status for all ML/calculation modules."
    ))
    return s


def _sec_appendix_glossary():
    s = []
    s.append(_p("Appendix C. Glossary", "h1"))
    s.append(_tbl(
        [
            ["Term", "Definition"],
            ["Projected Time", "Current structurally supported race estimate"],
            ["Supported Range", "Uncertainty-aware interval around the projection midpoint"],
            ["Driver", "Mechanistic contributor whose contribution sums to total improvement"],
            ["Baseline", "Anchor performance for computing improvement deltas"],
            ["Structural Shift", "Minimum change threshold (2s) for user-visible updates"],
            ["Model Source", "Label identifying the serving branch (deterministic/lstm)"],
            ["Fallback Reason", "Why a non-default serving branch reverted to deterministic"],
            ["Readiness", "Race-preparedness score (distinct from capability projection)"],
            ["Risk Band", "Low/moderate/high injury-risk classification"],
            ["Rollout Gate", "Runtime feature-flag or cohort-percentage control"],
            ["Non-primary", "Implemented module outside the default serving path"],
        ],
        [0.26 * TBL_W, 0.74 * TBL_W],
        "Table C1. Locked terminology and definitions."
    ))
    return s


def _sec_appendix_nonprimary():
    s = []
    s.append(_p("Appendix D. Non-Primary Module Algorithms", "h1"))
    s.extend(_ps([
        "The following modules are implemented in the codebase but are not "
        "part of the default serving path. They are documented here for "
        "completeness and to support future integration decisions.",
    ]))
    s.append(_p("D.1 Local Matrix Completion (LMC)", "h2"))
    s.extend(_ps([
        "LMC predicts race times across distances from sparse multi-distance "
        "results using rank-based matrix completion in log-time space [2]. "
        "The approach learns a runner-specific coefficient vector from "
        "available results and uses it to predict missing event times:",
    ]))
    s.append(_eq("log_time_pred = dot(lambda_hat, f_target)", 84))
    s.append(Spacer(1, 2))
    s.append(_eq("time_pred = exp(log_time_pred)", 85))
    s.append(Spacer(1, 2))
    s.append(_eq("lambda_0 clipped to [1.08, 1.15]   (endurance coeff)", 86))
    s.append(Spacer(1, 2))
    s.append(_eq("lambda_1 clipped to [-0.4, 0.4]   (speed-endurance)", 87))
    s.append(Spacer(1, 3))
    s.extend(_ps([
        "The supported range for LMC predictions uses an exponential "
        "uncertainty model: lower = pred * exp(-unc * mult), "
        "upper = pred * exp(+unc * mult). LMC is not in the primary "
        "serving path because the deterministic projection engine provides "
        "sufficient accuracy for users with adequate training data, and "
        "LMC's strength (sparse multi-distance inference) applies to a "
        "narrower user segment.",
    ]))

    s.append(_p("D.2 Learning heuristics", "h2"))
    s.extend(_ps([
        "The learning module applies trend and risk heuristics to feature "
        "deltas. A volume phase trigger fires at +/-15% three-week distance "
        "shift. A high threshold density trigger fires when z4_pct exceeds "
        "0.15. A risk trigger fires when acwr_4w exceeds 1.5. These "
        "heuristics generate advisory signals consumed by the chat agent "
        "and learning insights views rather than modifying projection state.",
    ]))

    s.append(_p("D.3 SHAP TreeExplainer", "h2"))
    s.extend(_ps([
        "When a trained Gradient Boosting model is available, SHAP "
        "TreeExplainer computes exact Shapley values for each of the "
        "17 input features. Per-driver SHAP totals are aggregated by "
        "summing the Shapley values of features belonging to each driver "
        "domain. The sign and magnitude of these totals determine driver "
        "direction (improving, declining, or stable) and generate the "
        "natural-language narrative explanations surfaced to users.",

        "The heuristic ratio-based explainer serves as fallback when no "
        "trained model exists. It computes feature-to-baseline ratios "
        "and buckets them into above/average/below categories, providing "
        "a SHAP-like decomposition suitable for deterministic-path "
        "explanations where true Shapley values are not computable.",
    ]))

    s.append(_p("Appendix E. Edge-Case Policies", "h1"))
    s.append(_tbl(
        [
            ["Equation / signal", "Bound or rule", "Rationale"],
            ["feature_score", "clip(0, 100)", "No single-feature domination"],
            ["max_improvement", "base * 0.25", "Block unrealistic claims"],
            ["raw_projected", ">= 60 s", "Physiological floor"],
            ["alpha dampening", "[0.3, 0.7]", "Responsiveness vs inertia"],
            ["structural shift", ">= 2.0 s", "Suppress noise"],
            ["volatility term", "cap 5%", "Prevent range blowup"],
            ["acwr range add", "+1% outside [0.6,1.5]", "Load-imbalance flag"],
            ["event exponent k", "[1.01, 1.15]", "Plausible transfer only"],
            ["risk probability", "clip [0, 1]", "Probabilistic validity"],
            ["risk bands", "lo<0.35, mod<0.60", "Actionable categories"],
            ["rollout bucket", "hash%100 < pct", "Stable cohort gating"],
            ["LSTM artifact", "fallback if absent", "No silent serve failures"],
            ["tiered baseline", "1->5 fallback", "Graceful degradation"],
            ["inactivity>10d", "range widen 5%", "Confidence decay signal"],
            ["inactivity>21d", "status=Declining", "Staleness label"],
            ["bias threshold", "|bias|>10 s", "Monitoring alert trigger"],
        ],
        [0.28 * TBL_W, 0.32 * TBL_W, 0.40 * TBL_W],
        "Table E1. Complete guardrail and edge-case policy catalog."
    ))

    s.append(_p("Appendix F. Rollout Scenario Matrix", "h1"))
    s.append(_tbl(
        [
            ["Scenario", "Condition", "Expected outcome"],
            ["S1", "LSTM flag disabled", "Det. serve; reason logged"],
            ["S2", "Outside rollout bucket", "Det. serve; gate reason logged"],
            ["S3", "LSTM selected, artifact missing", "Det. fallback; reason persisted"],
            ["S4", "LSTM valid, bounded pred.", "Override accepted w/ confidence"],
            ["S5", "Metric write failure", "Pipeline continues; warning logged"],
            ["S6", "High ACWR instability", "Range widens; readiness penalized"],
            ["S7", "No recent valid runs", "Conservative baseline; low confidence"],
            ["S8", "Large baseline shift (race)", "Dampening bypass; vol. reset"],
            ["S9", "Rollout pct changed", "Hash bucket stable across changes"],
            ["S10", "Old row missing metadata", "Frontend renders defaults"],
        ],
        [0.10 * TBL_W, 0.40 * TBL_W, 0.50 * TBL_W],
        "Table F1. Rollout and failure-mode scenarios with expected system behavior."
    ))
    return s


def _sec_references():
    s = []
    s.append(_p("References", "h1"))
    s.extend(_ps([
        "[1] Riegel, P.S. Athletic Records and Human Endurance. "
        "<i>American Scientist</i>, 69(3), 285-290, 1981.",

        "[2] Blythe, D.A.J. and Kiraly, F.J. Prediction and Quantification "
        "of Individual Athletic Performance of Runners. "
        "<i>PLOS ONE</i>, 11(6), e0157257, 2016.",

        "[3] Dash, S. Win Your Race Goal: A Generalized Approach to "
        "Prediction of Running Performance. "
        "<i>Sports Medicine International Open</i>, 8, a22351480, 2024.",

        "[4] Chang, P. et al. Identification of Runner Fatigue Stages "
        "Based on Inertial Sensors and Deep Learning. "
        "<i>Frontiers in Bioengineering and Biotechnology</i>, 11, 2023.",

        "[5] PIRX repository: verified implementation modules, README "
        "technical deltas, and migration records (current branch state).",
    ], "ref"))
    return s


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------

def build():
    doc = BaseDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title="The Science Behind PIRX",
        author="PIRX Engineering",
    )

    full_frame = Frame(
        doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="full")
    c1 = Frame(
        doc.leftMargin, doc.bottomMargin, COL_W, doc.height, id="c1")
    c2 = Frame(
        doc.leftMargin + COL_W + GAP, doc.bottomMargin, COL_W, doc.height, id="c2")

    doc.addPageTemplates([
        PageTemplate(id="title_page", frames=[full_frame], onPage=_on_page),
        PageTemplate(id="two_col", frames=[c1, c2], onPage=_on_page),
    ])

    story = []

    # Title page (single column)
    story.extend(_title_page())
    story.append(NextPageTemplate("two_col"))
    story.append(PageBreak())

    # Body (two column)
    story.extend(_sec_intro())
    story.extend(_sec_pipeline())
    story.extend(_sec_cleaning())
    story.extend(_sec_features())
    story.extend(_sec_baseline())
    story.extend(_sec_projection())
    story.extend(_sec_constants())
    story.extend(_sec_scaling())
    story.extend(_sec_readiness())
    story.extend(_sec_orchestration())
    story.extend(_sec_operational())
    story.extend(_sec_validation())
    story.extend(_sec_api_calcs())
    story.extend(_sec_pattern_detection())
    story.extend(_sec_discussion())
    story.extend(_sec_limitations())
    story.extend(_sec_future())
    story.extend(_sec_conclusion())

    # Appendices
    story.extend(_sec_appendix_formulas())
    story.extend(_sec_appendix_modules())
    story.extend(_sec_appendix_status())
    story.extend(_sec_appendix_glossary())
    story.extend(_sec_appendix_nonprimary())

    # References
    story.extend(_sec_references())

    doc.build(story)
    print(f"Wrote {OUT_PDF}  ({OUT_PDF.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    build()
