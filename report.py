from __future__ import annotations

import io
import numpy as np
import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from viz import fig_possession_outcomes, fig_xthreat_timeseries, fig_threat_heatmap, fig_progression_map


def _fig_to_png_bytes(fig, dpi=160):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    return buf


def build_pdf_report(df: pd.DataFrame, state, title: str, analyst_name: str | None = None) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 0.15 * inch))

    meta = [f"<b>Opposition:</b> {state.opposition}"]
    meta.append(f"<b>Matches:</b> {len(state.match_ids):,}")
    if state.has_dates and getattr(state, "date_start", None) and getattr(state, "date_end", None):
        meta.append(f"<b>Date range:</b> {state.date_start} to {state.date_end}")
    if state.phases:
        meta.append(f"<b>Phases:</b> {', '.join(state.phases[:6])}{'…' if len(state.phases)>6 else ''}")

    if analyst_name:
        meta.insert(0, f"<b>Analyst:</b> {analyst_name}")

    for line in meta:
        story.append(Paragraph(line, styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    # Metrics
    total_xthreat = float(df["xthreat"].fillna(0).sum()) if "xthreat" in df.columns else np.nan
    possessions = int(df["team_possession_id"].nunique()) if "team_possession_id" in df.columns else None
    rows = [
        ["Rows", f"{len(df):,}"],
        ["Matches", f"{df['match_id'].nunique():,}"],
        ["Possessions (approx)", f"{possessions:,}" if possessions is not None else "—"],
        ["Total xThreat", f"{total_xthreat:.2f}" if np.isfinite(total_xthreat) else "—"],
    ]
    t = Table(rows, colWidths=[2.4 * inch, 4.6 * inch])
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    figs = [
        ("Possession outcomes", fig_possession_outcomes(df)),
        ("Threat creation heatmap", fig_threat_heatmap(df)),
        ("xThreat over time", fig_xthreat_timeseries(df)),
        ("Progression map", fig_progression_map(df)),
    ]

    for heading, fig in figs:
        story.append(Paragraph(heading, styles["Heading1"]))
        story.append(Spacer(1, 0.15 * inch))
        img = Image(_fig_to_png_bytes(fig), width=7.1 * inch, height=4.7 * inch)
        story.append(img)
        story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
