#!/usr/bin/env python3
"""Build a full-length PIRX science paper PDF using ReportLab.

Target profile: 12-15 pages, two-column, narrative + technical depth.
"""

from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_PDF = ROOT / "docs" / "The_Science_Behind_PIRX.pdf"


def styles():
    s = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=s["Title"],
            fontName="Times-Bold",
            fontSize=19,
            leading=23,
            alignment=1,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=s["BodyText"],
            fontName="Times-Italic",
            fontSize=10,
            leading=13,
            alignment=1,
            spaceAfter=9,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=s["Heading2"],
            fontName="Times-Bold",
            fontSize=12,
            leading=14,
            spaceBefore=9,
            spaceAfter=4,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=s["Heading3"],
            fontName="Times-Bold",
            fontSize=10.3,
            leading=12.5,
            spaceBefore=6,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body",
            parent=s["BodyText"],
            fontName="Times-Roman",
            fontSize=9.1,
            leading=11.6,
            alignment=4,
            spaceAfter=4,
        ),
        "lead": ParagraphStyle(
            "lead",
            parent=s["BodyText"],
            fontName="Times-Roman",
            fontSize=9.4,
            leading=12.2,
            alignment=4,
            spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=s["BodyText"],
            fontName="Times-Roman",
            fontSize=8.8,
            leading=11,
            leftIndent=10,
            firstLineIndent=-6,
            spaceAfter=2,
        ),
        "cap": ParagraphStyle(
            "cap",
            parent=s["BodyText"],
            fontName="Times-Italic",
            fontSize=8.1,
            leading=10,
            alignment=1,
            spaceAfter=5,
        ),
        "ref": ParagraphStyle(
            "ref",
            parent=s["BodyText"],
            fontName="Times-Roman",
            fontSize=8.6,
            leading=10.8,
            spaceAfter=2,
        ),
    }


def tbl(data, widths):
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ebeff5")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafcff")]),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.3),
                ("LEADING", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return t


def rule(width=470):
    d = Drawing(width, 6)
    d.add(Line(0, 2, width, 2, strokeColor=colors.HexColor("#8a8a8a")))
    return d


def fig_pipeline():
    d = Drawing(470, 90)
    nodes = [("Ingest", 10), ("Clean", 103), ("Features", 196), ("Projection", 289), ("Persist", 382)]
    for label, x in nodes:
        d.add(Rect(x, 40, 78, 26, strokeColor=colors.black, fillColor=colors.white))
        d.add(String(x + 39, 51, label, textAnchor="middle", fontName="Times-Roman", fontSize=8))
    for x in [88, 181, 274, 367]:
        d.add(Line(x, 53, x + 15, 53, strokeColor=colors.black))
    d.add(Rect(145, 8, 180, 20, strokeColor=colors.black, fillColor=colors.white))
    d.add(String(235, 16, "APIs + Frontend + Chat + Realtime", textAnchor="middle", fontName="Times-Roman", fontSize=8))
    d.add(Line(421, 40, 235, 28, strokeColor=colors.black))
    return d


def fig_rollout():
    d = Drawing(470, 95)
    d.add(Rect(12, 56, 120, 24, strokeColor=colors.black, fillColor=colors.white))
    d.add(String(72, 66, "ModelOrchestrator", textAnchor="middle", fontName="Times-Roman", fontSize=8))
    d.add(Rect(166, 64, 95, 18, strokeColor=colors.black, fillColor=colors.white))
    d.add(String(213, 71, "deterministic", textAnchor="middle", fontName="Times-Roman", fontSize=8))
    d.add(Rect(166, 38, 95, 18, strokeColor=colors.black, fillColor=colors.white))
    d.add(String(213, 45, "lstm (gated)", textAnchor="middle", fontName="Times-Roman", fontSize=8))
    d.add(Rect(295, 38, 95, 18, strokeColor=colors.black, fillColor=colors.white))
    d.add(String(342, 45, "LSTM adapter", textAnchor="middle", fontName="Times-Roman", fontSize=8))
    d.add(Rect(295, 12, 158, 18, strokeColor=colors.black, fillColor=colors.white))
    d.add(String(374, 19, "fallback -> deterministic", textAnchor="middle", fontName="Times-Roman", fontSize=8))
    d.add(Line(132, 68, 166, 71, strokeColor=colors.black))
    d.add(Line(132, 63, 166, 46, strokeColor=colors.black))
    d.add(Line(261, 46, 295, 46, strokeColor=colors.black))
    d.add(Line(342, 38, 342, 30, strokeColor=colors.black))
    return d


def fig_uncertainty():
    d = Drawing(470, 92)
    d.add(Rect(12, 44, 105, 24, strokeColor=colors.black, fillColor=colors.white))
    d.add(String(65, 53, "Base 1.5%", textAnchor="middle", fontName="Times-Roman", fontSize=8))
    d.add(Rect(132, 44, 105, 24, strokeColor=colors.black, fillColor=colors.white))
    d.add(String(184, 53, "Volatility term", textAnchor="middle", fontName="Times-Roman", fontSize=8))
    d.add(Rect(252, 44, 105, 24, strokeColor=colors.black, fillColor=colors.white))
    d.add(String(304, 53, "Data quality term", textAnchor="middle", fontName="Times-Roman", fontSize=8))
    d.add(Rect(372, 44, 86, 24, strokeColor=colors.black, fillColor=colors.white))
    d.add(String(415, 53, "ACWR term", textAnchor="middle", fontName="Times-Roman", fontSize=8))
    d.add(Line(117, 56, 132, 56, strokeColor=colors.black))
    d.add(Line(237, 56, 252, 56, strokeColor=colors.black))
    d.add(Line(357, 56, 372, 56, strokeColor=colors.black))
    d.add(Rect(150, 10, 170, 20, strokeColor=colors.black, fillColor=colors.white))
    d.add(String(235, 17, "total_pct -> range_low/high", textAnchor="middle", fontName="Times-Roman", fontSize=8))
    d.add(Line(235, 44, 235, 30, strokeColor=colors.black))
    return d


def on_page(canvas, _doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 8)
    canvas.drawString(12 * mm, 8 * mm, "PIRX Science Paper")
    canvas.drawRightString(A4[0] - 12 * mm, 8 * mm, str(canvas.getPageNumber()))
    canvas.restoreState()


def add_para_block(story, style, paragraphs):
    for p in paragraphs:
        story.append(Paragraph(p, style))


def build():
    st = styles()
    doc = BaseDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="The Science Behind PIRX",
        author="PIRX Engineering",
    )
    full = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="full")
    gap = 8 * mm
    colw = (doc.width - gap) / 2
    c1 = Frame(doc.leftMargin, doc.bottomMargin, colw, doc.height, id="c1")
    c2 = Frame(doc.leftMargin + colw + gap, doc.bottomMargin, colw, doc.height, id="c2")
    doc.addPageTemplates([PageTemplate(id="title", frames=[full], onPage=on_page), PageTemplate(id="paper", frames=[c1, c2], onPage=on_page)])

    story = []
    story.append(Paragraph("The Science Behind PIRX", st["title"]))
    story.append(Paragraph("A Narrative and Technical Account of Calculations, ML Components, and Rollout Safety", st["subtitle"]))
    add_para_block(
        story,
        st["lead"],
        [
            "<b>Abstract.</b> PIRX provides race projections from wearable and training history data using a projection-first architecture. This paper documents formulas, constants, ML components, and serving orchestration in a single technical narrative.",
            "The primary contribution is architectural: deterministic equations remain the reliability floor, while model-based personalization is introduced through explicit flags, cohort gates, and audited fallback behavior.",
            "This aligns with academic reporting patterns in the studies corpus: state the problem clearly, define method choices with assumptions, separate implemented results from planned extensions, and declare limitations directly.",
        ],
    )
    story.append(rule())

    story.append(PageBreak())
    story.append(Paragraph("Appendix J. End-to-End Trace Example", st["h1"]))
    trace_steps = [
        "Step 1: User sync brings in 12 new activities from wearable providers.",
        "Step 2: Cleaning removes two invalid sessions (pace/elevation anomalies), leaving ten admissible runs.",
        "Step 3: Feature service recomputes rolling windows and ACWR family.",
        "Step 4: Baseline estimator resolves anchor via tiered chain; if default-triggered, KNN cold-start is attempted.",
        "Step 5: Orchestrator evaluates serving branch using flags, rollout bucket, and active model metadata.",
        "Step 6: If deterministic branch selected, projection engine computes midpoint/range directly from driver scoring.",
        "Step 7: If LSTM selected but artifact unavailable, explicit fallback to deterministic is applied.",
        "Step 8: Driver decomposition persisted with sum-preserving contributions.",
        "Step 9: Model serving decision metric is written for observability.",
        "Step 10: Structural shift logic determines whether the update is user-visible.",
        "Step 11: APIs and realtime streams expose current state with provenance metadata.",
        "Step 12: Frontend renders projection + confidence context without breaking backward compatibility for older rows.",
    ]
    for s in trace_steps:
        story.append(Paragraph(s, st["body"]))
    story.append(
        tbl(
            [
                ["Trace field", "Example value", "Interpretation"],
                ["event", "5000", "distance context for projection record"],
                ["model_source", "deterministic", "serving branch that produced state"],
                ["model_confidence", "0.72 (if model-based)", "confidence payload for UI/context"],
                ["fallback_reason", "fallback_from_lstm_unavailable", "explicit reason for branch reversal"],
                ["total_improvement_seconds", "14.8", "aggregate improvement vs baseline"],
                ["range_low / range_high", "1310 / 1382", "supported range window"],
            ],
            [45 * mm, 45 * mm, 62 * mm],
        )
    )
    story.append(Paragraph("Table J1. Example trace fields and interpretation semantics.", st["cap"]))
    story.append(rule())

    story.append(PageBreak())
    story.append(Paragraph("Appendix K. Release Governance Notes", st["h1"]))
    governance = [
        "Gate 1: Schema readiness (lifecycle and metadata contracts present).",
        "Gate 2: Serving controls present (`enable_lstm_serving`, rollout percentage).",
        "Gate 3: Metric pathways healthy (serving decisions, readiness signals, bias/error tasks).",
        "Gate 4: Failure-mode tests confirm deterministic continuity under observability or artifact faults.",
        "Gate 5: Frontend metadata rendering remains backward compatible with older rows.",
        "Gate 6: Documentation labels match operational truth (active, gated, non-primary).",
        "Gate 7: Rollout endpoint checks green before percentage increases.",
        "Gate 8: Incremental cohort expansion with explicit rollback path.",
    ]
    for g in governance:
        story.append(Paragraph(g, st["body"]))
    story.append(
        tbl(
            [
                ["Rollout stage", "Typical percentage", "Decision criteria to advance"],
                ["Stage 0", "0%", "contracts and tests complete, no live ML serving"],
                ["Stage 1", "5-10%", "no critical fallback spikes, stable API behavior"],
                ["Stage 2", "25%", "confidence distribution reasonable, no user-facing regressions"],
                ["Stage 3", "50%", "extended stability window met, on-call confidence high"],
                ["Stage 4", "100%", "release-readiness checks pass and rollback confidence retained"],
            ],
            [36 * mm, 34 * mm, 82 * mm],
        )
    )
    story.append(Paragraph("Table K1. Example staged rollout progression for model serving.", st["cap"]))
    story.append(rule())

    story.append(PageBreak())
    story.append(Paragraph("Appendix L. Glossary and Terminology Guardrails", st["h1"]))
    story.append(
        tbl(
            [
                ["Term", "Definition", "Usage rule"],
                ["Projected Time", "Current structurally supported race estimate", "Primary capability metric"],
                ["Supported Range", "Uncertainty-aware interval around projection", "Must be shown with midpoint"],
                ["Driver", "Mechanistic contributor to projection change", "Contributions sum to total improvement"],
                ["Baseline", "Anchor performance used for deltas", "Tiered estimator with fallbacks"],
                ["Structural Shift", "Meaningful state change threshold", "User-visible shift >= 2s"],
                ["Model Source", "Serving branch label", "Expose deterministic vs model branch"],
                ["Fallback Reason", "Why non-default branch reverted", "Persist and surface for interpretability"],
                ["Readiness", "Race-preparedness score context", "Distinct from projection capability"],
                ["Risk Band", "Low/moderate/high injury-risk class", "Additive context, not projection overwrite"],
                ["Rollout Gate", "Runtime controls for model serving", "Required before branch activation"],
                ["Non-primary module", "Implemented module outside default serving path", "Label explicitly in docs"],
            ],
            [30 * mm, 70 * mm, 52 * mm],
        )
    )
    story.append(Paragraph("Table L1. Terminology used to prevent ambiguity in product and science communication.", st["cap"]))
    add_para_block(
        story,
        st["body"],
        [
            "Terminology discipline is part of safety. Ambiguous labels can cause users or operators to misunderstand whether a value is a capability estimate, readiness context, or model experiment output.",
            "This glossary aligns narrative wording with implementation contracts and UI metadata fields.",
        ],
    )
    story.append(Spacer(1, 4))
    story.append(NextPageTemplate("paper"))
    story.append(PageBreak())

    story.append(Paragraph("1. Introduction", st["h1"]))
    add_para_block(
        story,
        st["body"],
        [
            "Running-performance forecasting methods often trade interpretability for raw predictive power. PIRX addresses this tradeoff by designing around interpretability first: every output state is traceable to a known formula path, bounded uncertainty logic, and explicit metadata about model source.",
            "The system objective is not merely to provide a number, but to provide a defensible answer to: <i>what does current training structurally support right now, and why</i>. This distinction drives both equation design and rollout policy.",
            "As in the study references, this document emphasizes both narrative rationale and method transparency. The user-facing outputs (Projected Time, Supported Range, readiness context) are derived from deterministic calculations that can be inspected and reproduced.",
        ],
    )
    story.append(Paragraph("• Objective: stable, interpretable, and auditable projection updates.", st["bullet"]))
    story.append(Paragraph("• Scope: formulas, constants, ML status, rollout controls, and validation metrics.", st["bullet"]))
    story.append(rule())

    story.append(Paragraph("2. Methods", st["h1"]))
    story.append(Paragraph("2.1 System pipeline and processing stages", st["h2"]))
    add_para_block(
        story,
        st["body"],
        [
            "PIRX runs a pipeline: ingest -> clean -> feature engineer -> projection recompute -> persistence -> API/frontend/chat exposure. The ordering is intentional. Cleaning gates remove invalid sessions before signal aggregation, reducing downstream distortion and improving stability.",
            "Feature engineering then computes domain-specific metrics (volume, intensity, efficiency, consistency, physiology). Projection recompute consumes these features with baseline and prior state to produce midpoint/range updates and driver contribution decomposition.",
            "Finally, state is persisted for APIs and realtime consumers, with model-provenance metadata attached. This architecture ensures that UI/analytics layers are downstream of a single source of computational truth.",
        ],
    )
    story.append(fig_pipeline())
    story.append(Paragraph("Figure 1. End-to-end PIRX data flow, from ingestion to user surfaces.", st["cap"]))

    story.append(Paragraph("2.2 Data cleaning and quality gates", st["h2"]))
    story.append(
        tbl(
            [
                ["Signal", "Rule", "Why it exists"],
                ["Allowed activity types", "easy / threshold / interval / race", "Prevents non-run sessions from contaminating model inputs"],
                ["Non-race minima", "duration >= 180 s and distance >= 1600 m", "Filters very short or accidental sessions"],
                ["Race minima", "duration >= 60 s and distance >= 400 m", "Allows valid short race efforts without opening noise too far"],
                ["Pace bounds", "223 <= pace_sec_per_km <= 900", "Rejects impossible/faulty pace records"],
                ["Relative outlier", "reject if pace > 1.5 * runner_avg_pace", "Suppresses personalized outliers beyond static global bounds"],
                ["Elevation quality", "reject long outdoor run with zero elevation", "Detects likely sensor/data artifacts"],
            ],
            [38 * mm, 43 * mm, 71 * mm],
        )
    )
    story.append(Paragraph("Table 1. Cleaning rules and rationale prior to feature computation.", st["cap"]))

    story.append(Paragraph("2.3 Feature engineering and temporal weighting", st["h2"]))
    add_para_block(
        story,
        st["body"],
        [
            "Feature windows prioritize recency while preserving structural context. The weighted aggregation is: weighted_feature_score = 0.45*W_7d + 0.35*W_8_21d + 0.20*W_22_90d, where each term is a normalized window summary.",
            "ACWR is implemented with EWMA for acute/chronic load, improving stability over naive rolling-ratio implementations. The three ACWR windows (4w, 6w, 8w) support both readiness context and uncertainty widening decisions.",
            "In addition to load metrics, PIRX computes efficiency and consistency signals. This is critical: volume-only systems can overvalue quantity while missing structural instability; PIRX explicitly scores both capacity and control.",
        ],
    )
    story.append(
        tbl(
            [
                ["Domain", "Representative features", "Equation summary"],
                ["Volume", "rolling_distance_7d/21d/42d/90d", "windowed sums over valid runs"],
                ["Intensity", "z1-z5, threshold_density, speed_exposure", "zone proportions + weekly normalized hard-load minutes"],
                ["Efficiency", "matched_hr_band_pace, hr_drift, pace_decay", "pace behavior at comparable physiological demand"],
                ["Consistency", "weekly_load_stddev, block_variance, session_stability", "dispersion metrics over recent blocks"],
                ["Physiology", "resting_hr_trend, hrv_trend, sleep_score_trend", "trend direction and magnitude indicators"],
            ],
            [28 * mm, 57 * mm, 67 * mm],
        )
    )
    story.append(Paragraph("Table 2. Feature domains and representative calculations.", st["cap"]))

    story.append(Paragraph("2.4 Projection model equations", st["h2"]))
    add_para_block(
        story,
        st["body"],
        [
            "Projection starts from baseline time and applies weighted driver scoring: weighted_sum = sum(driver_score_d * weight_d). Improvement factor = (weighted_sum - 50) / 50, capped by max_improvement = baseline_time * 0.25.",
            "Raw projection is then bounded: raw_projected = max(baseline_time - total_improvement_seconds, 60). This prevents pathological outputs and keeps values in physically plausible space.",
            "Volatility dampening blends new and previous state using alpha in [0.3, 0.7], and user-visible structural updates require absolute shift >= 2.0 seconds.",
        ],
    )
    story.append(
        tbl(
            [
                ["Constant", "Value", "Role in model behavior"],
                ["Structural shift threshold", "2.0 seconds", "Prevents UI churn from small noise"],
                ["Max improvement cap", "25% of baseline", "Bounds optimism and over-fit drift"],
                ["Dampening alpha bounds", "[0.3, 0.7]", "Controls projection inertia"],
                ["Range base pct", "1.5%", "Default uncertainty floor"],
                ["Volatility cap term", "min(volatility/projected, 0.05)", "Prevents runaway uncertainty spikes"],
                ["Data quality term", "(1-data_quality)*0.02", "Penalizes sparse feature coverage"],
                ["ACWR range add", "+1% outside [0.6,1.5]", "Flags unstable load balance in uncertainty"],
            ],
            [35 * mm, 27 * mm, 90 * mm],
        )
    )
    story.append(Paragraph("Table 3. Projection constants and the behavior each constant controls.", st["cap"]))

    story.append(Paragraph("2.5 Event scaling model", st["h2"]))
    add_para_block(
        story,
        st["body"],
        [
            "Cross-distance prediction uses Riegel scaling: T2 = T1 * (D2/D1)^k. The default exponent is 1.06, with individualized bounds [1.01, 1.15].",
            "PIRX includes volume-aware adjustment of k and boundary handling at 5K transitions (+/-0.02), capturing asymmetry between shorter and longer event transfer.",
            "Environmental adjustment applies a linear penalty outside the 10-17.5 C optimal band: multiplier = 1 + 0.0035*degrees_outside.",
        ],
    )

    story.append(Paragraph("2.6 Readiness and injury-risk logic", st["h2"]))
    add_para_block(
        story,
        st["body"],
        [
            "Readiness score combines ACWR balance, freshness, training recency, physiological trend, and consistency bonus. The weighted score is clipped to [0,100] and mapped to implementation labels.",
            "Injury risk is additive to readiness context and intentionally does not mutate projection state directly. This separation avoids conflating capability estimation with risk advisory signals.",
            "Risk probability is calibrated into low/moderate/high bands and persisted for operational traceability.",
        ],
    )
    story.append(fig_uncertainty())
    story.append(Paragraph("Figure 2. Supported-range uncertainty composition from base, volatility, data quality, and ACWR terms.", st["cap"]))

    story.append(Paragraph("2.7 Model orchestration and rollout safety", st["h2"]))
    add_para_block(
        story,
        st["body"],
        [
            "Selection is centralized in ModelOrchestrator. Deterministic remains default. LSTM serving is only eligible when feature flag and rollout bucket checks pass.",
            "If active model artifacts are absent/unusable, serving path falls back to deterministic and records fallback_reason metadata. This policy ensures no silent hard failure in projection recompute.",
            "KNN exists in baseline fallback path; ML lifecycle entities track training/tuning artifacts for auditability and promotion control.",
        ],
    )
    story.append(fig_rollout())
    story.append(Paragraph("Figure 3. Serving decision topology with guarded LSTM path and deterministic fallback.", st["cap"]))
    story.append(rule())

    story.append(Paragraph("3. Results", st["h1"]))
    add_para_block(
        story,
        st["body"],
        [
            "Repository verification confirms that major ML-gap items are present with explicit state separation between active and rollout-gated components.",
            "Operational endpoints expose rollout posture and serving metrics, enabling staged release management without direct database inspection.",
            "This architecture produces two practical outcomes: stable deterministic baseline behavior and incremental personalization under controlled risk.",
        ],
    )
    story.append(
        tbl(
            [
                ["Component", "Status", "Operational implication"],
                ["Deterministic projection engine", "Implemented and active", "Reliability floor for all users"],
                ["KNN cold-start baseline", "Implemented and active", "Reduces default-baseline brittleness for sparse users"],
                ["LSTM inference adapter", "Implemented but rollout-gated", "Optional personalization without unsafe default switch"],
                ["Optuna lifecycle + promotion", "Implemented but rollout-gated", "Supports auditable tuning and guarded promotion"],
                ["Injury-risk RF", "Implemented and active", "Adds risk context to readiness without mutating projection"],
                ["LMC module", "Implemented, non-primary", "Alternative modeling path not primary serving default"],
                ["SHAP explainer heuristics", "Implemented, non-primary", "Secondary explainability support outside serving selector"],
            ],
            [48 * mm, 42 * mm, 62 * mm],
        )
    )
    story.append(Paragraph("Table 4. Verified implementation status and operational effect.", st["cap"]))

    story.append(Paragraph("4. Discussion", st["h1"]))
    add_para_block(
        story,
        st["body"],
        [
            "A recurring failure mode in sports prediction systems is opacity: users cannot determine whether changes are physiologically meaningful or model noise. PIRX mitigates this with thresholds, range semantics, and provenance metadata.",
            "Another failure mode is uncontrolled model rollout. PIRX addresses this by requiring both infrastructure readiness and cohort gating before switching live serving branches.",
            "From a coaching perspective, this architecture supports interpretation: users can connect projections to driver changes and training structure rather than treating outputs as unexplained black-box scores.",
            "The study references highlight the value of parsimonious explanatory structures; PIRX follows this by preserving deterministic equation interpretability even while adding modern ML infrastructure.",
        ],
    )

    story.append(Paragraph("5. Limitations", st["h1"]))
    add_para_block(
        story,
        st["body"],
        [
            "Some model paths remain scaffolded and rollout-gated by design. This is a deliberate safety choice, but it also means fully personalized serving behavior is not yet the default for all users.",
            "Current document-level figures are schematic (architecture-oriented) rather than empirical plots from held-out benchmark cohorts. Future versions should add richer quantitative performance tables when shared benchmark protocols are finalized.",
            "As with all wearable-driven systems, upstream sensor quality and labeling consistency remain external constraints despite aggressive cleaning and outlier controls.",
        ],
    )

    story.append(Paragraph("6. Practical Why (Design Rationale)", st["h1"]))
    add_para_block(
        story,
        st["body"],
        [
            "Why deterministic-first? Because users must trust that state changes are explainable before they trust that state changes are optimal.",
            "Why range outputs? Because race support is uncertain by nature and single-point predictions overstate certainty.",
            "Why rollout gates? Because safe migration from deterministic to ML serving requires observability, fallback, and reversible control planes.",
            "Why explicit status labels in documentation? Because conflating implemented and planned behavior creates product and clinical risk.",
        ],
    )

    story.append(Paragraph("7. Conclusion", st["h1"]))
    add_para_block(
        story,
        st["body"],
        [
            "PIRX combines transparent equation-based projection with controlled ML personalization. The key contribution is not only model choice but system design: data conditioning, bounded state updates, explicit uncertainty, and staged rollout governance.",
            "This architecture supports both scientific accountability and product reliability. As rollout-gated modules mature, personalization can increase without sacrificing interpretability and safety.",
        ],
    )

    story.append(Paragraph("Appendix A. Formula Catalog", st["h1"]))
    story.append(
        tbl(
            [
                ["Area", "Core equation"],
                ["Feature recency weighting", "weighted_feature_score = 0.45*W_7d + 0.35*W_8_21d + 0.20*W_22_90d"],
                ["EWMA load", "EWMA_t = alpha*load_t + (1-alpha)*EWMA_(t-1)"],
                ["ACWR", "ACWR = acute_load / chronic_load"],
                ["Improvement factor", "(weighted_sum - 50) / 50"],
                ["Raw projected time", "max(baseline - total_improvement_seconds, 60)"],
                ["Dampened projection", "alpha*raw + (1-alpha)*previous"],
                ["Range low/high", "projected*(1-total_pct), projected*(1+total_pct)"],
                ["Event scaling", "T2 = T1*(D2/D1)^k"],
            ],
            [55 * mm, 97 * mm],
        )
    )
    story.append(Paragraph("Table A1. Compact equation reference for implementation and review.", st["cap"]))

    story.append(Paragraph("Appendix B. Rollout and Monitoring Signals", st["h1"]))
    story.append(
        tbl(
            [
                ["Signal", "Location", "Purpose"],
                ["enable_lstm_serving", "runtime config", "global LSTM serving gate"],
                ["lstm_serving_rollout_percentage", "runtime config", "cohort rollout percentage"],
                ["model_source / model_confidence / fallback_reason", "projection metadata", "provenance + explainability"],
                ["/rollout/config", "API endpoint", "current rollout posture"],
                ["/rollout/metrics", "API endpoint", "serving-decision aggregation"],
                ["/rollout/release-readiness", "API endpoint", "gates + metrics readiness summary"],
            ],
            [44 * mm, 40 * mm, 68 * mm],
        )
    )
    story.append(Paragraph("Table B1. Operational controls and observability surfaces.", st["cap"]))

    story.append(Paragraph("Appendix C. Module-by-Module Computational Walkthrough", st["h1"]))
    add_para_block(
        story,
        st["body"],
        [
            "This appendix expands the operational narrative to the module level so readers can map conceptual stages to concrete backend implementation boundaries.",
            "Each module listed below contributes to either data validity, feature quality, projection integrity, model governance, or product explainability.",
        ],
    )
    story.append(
        tbl(
            [
                ["Module", "Primary responsibility", "Failure mode mitigated"],
                ["services/cleaning_service.py", "Activity admissibility filtering and normalization", "Garbage-in projection drift"],
                ["services/feature_service.py", "Rolling feature computation + ACWR family", "Sparse/noisy feature vectors"],
                ["ml/baseline_estimator.py", "Tiered 5K anchor selection", "Unstable baselines from single heuristic"],
                ["ml/reference_population.py", "KNN cold-start baseline support", "Default-anchor overuse"],
                ["ml/projection_engine.py", "Driver scoring, weighted improvement, range output", "Opaque projection jumps"],
                ["ml/event_scaling.py", "Cross-distance projection and exponent handling", "Distance transfer inconsistency"],
                ["ml/readiness_engine.py", "Readiness decomposition and label assignment", "Single-score oversimplification"],
                ["ml/trajectory_engine.py", "Scenario perturbation simulations", "Static-only interpretation"],
                ["services/model_orchestrator.py", "Serving branch selection + rollout gating", "Unsafe model cutover"],
                ["ml/lstm_inference.py", "Artifact-backed LSTM override candidate", "Unbounded model injection"],
                ["ml/injury_risk_model.py", "Additive risk probability + banding", "Projection/risk conflation"],
                ["tasks/ml_tasks.py", "Training/tuning lifecycle persistence", "Untracked model lineage"],
                ["routers/rollout.py", "Operational gate and metrics visibility", "Low observability rollouts"],
                ["services/driver_service.py", "Driver contribution persistence and decomposition", "Non-summing driver narratives"],
                ["tasks/projection_tasks.py", "Scheduled decay and backfill orchestration", "Stale projections in inactivity"],
                ["tasks/accuracy_tasks.py", "Error, bias, and agreement metrics", "Unmeasured drift"],
                ["routers/projection.py", "Projection API assembly and fallbacks", "UI contract fragility"],
                ["routers/readiness.py", "Readiness + risk output delivery", "Missing risk context"],
                ["services/supabase_client.py", "Typed persistence boundary", "Schema contract ambiguity"],
            ],
            [45 * mm, 61 * mm, 46 * mm],
        )
    )
    story.append(Paragraph("Table C1. Module responsibilities and the specific reliability risks they address.", st["cap"]))

    story.append(Paragraph("Appendix D. Equation Rationale and Edge-Case Policy", st["h1"]))
    add_para_block(
        story,
        st["body"],
        [
            "The following policy notes explain why each key equation includes clipping, caps, or thresholds. These controls are not cosmetic; they are safeguards against unstable user-facing states.",
            "In practice, most projection failures are not due to a single incorrect formula but due to unbounded interactions between formulas under sparse or noisy data. The policy table below documents those guardrails.",
        ],
    )
    story.append(
        tbl(
            [
                ["Equation / signal", "Bound or rule", "Design rationale"],
                ["feature_score", "clip(0,100)", "Prevents one feature from dominating driver score"],
                ["max_improvement", "baseline*0.25", "Prevents unrealistic improvement claims"],
                ["raw_projected", ">=60s", "Avoids invalid physiological outputs"],
                ["alpha dampening", "[0.3,0.7]", "Balances responsiveness and inertia"],
                ["structural shift display", ">=2.0s", "Suppresses presentation noise"],
                ["volatility term", "cap 5%", "Avoids runaway range expansion"],
                ["acwr range add", "+1% outside [0.6,1.5]", "Reflects load-imbalance instability"],
                ["event exponent k", "clamp [1.01,1.15]", "Limits implausible distance transfer"],
                ["risk probability", "clip [0,1]", "Probabilistic validity"],
                ["risk band thresholds", "low<0.35, mod<0.60", "Actionable categorical interpretation"],
                ["model rollout bucket", "hash%100<pct", "Stable cohort gating"],
                ["artifact-required LSTM serve", "fallback if absent", "No silent model serve failures"],
                ["tiered baseline fallback", "1->5 chain", "Graceful degradation under sparse history"],
            ],
            [43 * mm, 37 * mm, 72 * mm],
        )
    )
    story.append(Paragraph("Table D1. Guardrails that prevent unstable or misleading output states.", st["cap"]))

    story.append(Paragraph("Appendix E. Study-Alignment Narrative", st["h1"]))
    add_para_block(
        story,
        st["body"],
        [
            "The papers in Studies/ repeatedly follow a consistent logic: define the practical problem, motivate method choice, quantify performance, and acknowledge constraints. PIRX documentation now mirrors that structure.",
            "From generalized prediction literature, PIRX adopts cross-distance scaling and model comparison framing. From low-rank/power-law literature, PIRX adopts parsimonious summary concepts and individualized transfer logic. From fatigue modeling studies, PIRX adopts additive risk interpretation and careful statement of scope.",
            "Crucially, PIRX documentation distinguishes what is production-default from what is rollout-gated. This mirrors rigorous methods sections where model variants are disclosed rather than implied.",
            "The intent is not to claim equivalence with any single study design, but to carry forward reporting discipline: assumptions explicit, equations explicit, limits explicit, and operational controls explicit.",
        ],
    )

    long_form_notes = [
        "Why narrative depth matters: users and coaches evaluate trust not from RMSE alone but from whether changes are explainable session-to-session.",
        "Why page length matters in this context: short summaries hide assumptions and can blur production-default behavior with planned behavior.",
        "Why deterministic-first remains central: every new model path should inherit the same observability and fallback guarantees before default enablement.",
        "Why uncertainty must be shown as range not single point: data sparsity, volatility, and load imbalance have asymmetric impacts that point estimates conceal.",
        "Why model metadata should be user-visible: provenance and fallback reasons reduce confusion during rollout and make support/debug paths faster.",
        "Why table-heavy documentation is useful: equations and constants become testable contracts, not prose interpretations.",
        "Why appendices are included: operational reliability often depends on edge-case policy details that do not fit cleanly in abstract-level sections.",
        "Why this document is intentionally redundant in key places: repeated guardrail statements reduce misinterpretation during future refactors.",
        "Why rollout endpoints are part of science documentation: serving science in production is inseparable from monitoring and release controls.",
        "Why references are scoped: citations motivate methodology, while repository code remains source-of-truth for actual implemented behavior.",
    ]
    for note in long_form_notes:
        story.append(Paragraph(note, st["body"]))

    story.append(PageBreak())
    story.append(Paragraph("Appendix F. Detailed Feature Computation Notes", st["h1"]))
    feature_notes = [
        "Volume features are recomputed from cleaned activity records, never from raw ingestion payloads, to ensure consistency between historical backfill and incremental sync.",
        "Intensity features use zone proportions rather than absolute zone durations in isolation so that comparisons remain interpretable across variable weekly totals.",
        "Efficiency features are intentionally tied to matched heart-rate bands to avoid conflating fitness gain with temporary effort strategy changes.",
        "Consistency features are dispersion metrics rather than means, because adaptation reliability is better explained by variance control than by peak workload events.",
        "ACWR families (4w, 6w, 8w) are retained simultaneously to capture short-horizon instability without losing medium-horizon context.",
        "Physiological trend fields are used opportunistically when available, and uncertainty terms compensate when those features are missing.",
        "The weighting scheme is asymmetric by design: 7-day signal carries strongest influence while preserving an anchor to older training structure.",
        "Feature defaults are conservative to prevent accidental optimism in sparse-data scenarios.",
        "All feature values are computed in units that map cleanly to projection equations (seconds, meters, ratios).",
        "Edge-case policy: if valid runs are insufficient for a feature family, that family contributes reduced confidence rather than synthetic high-confidence estimates.",
    ]
    for p in feature_notes:
        story.append(Paragraph(p, st["body"]))
    story.append(rule())

    story.append(PageBreak())
    story.append(Paragraph("Appendix G. Projection and Driver Decomposition Notes", st["h1"]))
    driver_notes = [
        "Driver decomposition is constrained to sum exactly to total improvement seconds; this avoids narrative inconsistency between aggregate and component views.",
        "Rounding is handled with final-driver remainder assignment, which preserves arithmetic closure after precision formatting.",
        "Volatility dampening is bypassed on large baseline shifts to prevent stale inertia from masking major structural events.",
        "Supported Range communicates confidence context rather than expected race-day variance only; this distinction is central to user interpretation.",
        "Projection state persistence stores midpoint, range, baseline, model metadata, and confidence context in a single coherent event row.",
        "When confidence degrades under inactivity policy, range widening and confidence reduction are coordinated to preserve interpretive consistency.",
        "Projection updates are designed for append-only history semantics to support longitudinal analysis and avoid hidden state mutation side effects.",
        "Driver history allows trend classification that is independent from one-off projection jumps, improving explanatory continuity.",
        "API-level fallback safeguards preserve contract shape even when optional fields are missing.",
        "This decomposition design follows the same reporting principle used in scientific studies: aggregate effect must be explainable by constituent mechanisms.",
    ]
    for p in driver_notes:
        story.append(Paragraph(p, st["body"]))
    story.append(rule())

    story.append(PageBreak())
    story.append(Paragraph("Appendix H. Rollout Scenarios and Failure-Mode Handling", st["h1"]))
    rollout_notes = [
        "Scenario 1: LSTM flag disabled. Expected outcome: deterministic serve with explicit selector reason and no model override attempt.",
        "Scenario 2: LSTM flag enabled but user outside rollout bucket. Expected outcome: deterministic serve with rollout gate reason.",
        "Scenario 3: LSTM selected with active model but missing artifact. Expected outcome: deterministic fallback with fallback_reason persisted.",
        "Scenario 4: LSTM selected with valid artifact and bounded prediction. Expected outcome: projection override accepted with confidence metadata.",
        "Scenario 5: metric-write failure after projection computation. Expected outcome: projection pipeline continues and warning path recorded.",
        "Scenario 6: high ACWR instability. Expected outcome: readiness penalty and supported-range widening without direct projection mutation.",
        "Scenario 7: no recent valid runs. Expected outcome: conservative baseline fallback path with reduced confidence semantics.",
        "Scenario 8: large baseline shift from new high-quality race. Expected outcome: dampening bypass to avoid stale smoothing artifacts.",
        "Scenario 9: rollout percentage change during operations. Expected outcome: deterministic cohort membership based on stable hash bucketing.",
        "Scenario 10: frontend reads model metadata absent in older rows. Expected outcome: graceful rendering with backward-compatible defaults.",
    ]
    for p in rollout_notes:
        story.append(Paragraph(p, st["body"]))
    story.append(rule())

    story.append(PageBreak())
    story.append(Paragraph("Appendix I. Validation and Reporting Checklist", st["h1"]))
    checklist = [
        "Confirm formula parity between document and implementation modules.",
        "Confirm constants/threshold table matches active production values.",
        "Confirm status labels (active vs rollout-gated vs non-primary) match current code path.",
        "Confirm serving fallback reasons are represented in both API and narrative examples.",
        "Confirm rollout endpoints and gate semantics are still current.",
        "Confirm data-cleaning gates and pace bounds are unchanged.",
        "Confirm readiness risk remains additive and does not mutate projection state directly.",
        "Confirm PDF generation remains reproducible from repository-local tooling.",
        "Confirm references section aligns with studies used for narrative/format guidance.",
        "Confirm README delta includes why/change/verification fields for documentation updates.",
    ]
    for idx, item in enumerate(checklist, start=1):
        story.append(Paragraph(f"{idx}. {item}", st["body"]))
    story.append(rule())

    story.append(Paragraph("References", st["h1"]))
    refs = [
        "[1] Riegel PS. Athletic records and human endurance (1981).",
        "[2] Blythe DAJ, Kiraly FJ. Prediction and Quantification of Individual Athletic Performance of Runners (PLOS ONE, 2016).",
        "[3] Dash S. Win Your Race Goal: A Generalized Approach to Prediction of Running Performance (Sports Med Int Open, 2024).",
        "[4] Chang P, et al. Identification of runner fatigue stages based on inertial sensors and deep learning (Frontiers, 2023).",
        "[5] PIRX repository source modules and README technical deltas (current branch state).",
        "[6] Additional studies in repository Studies/ folder for layout and reporting pattern reference.",
    ]
    for r in refs:
        story.append(Paragraph(r, st["ref"]))

    doc.build(story)
    print(f"Wrote {OUT_PDF}")


if __name__ == "__main__":
    build()

