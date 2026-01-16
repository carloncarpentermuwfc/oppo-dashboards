from __future__ import annotations

import io
from dataclasses import asdict

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from viz import fig_event_type_bar, fig_touch_heatmap, fig_pass_map, fig_shot_map


def _fig_to_png_bytes(fig, dpi=160):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    return buf


def build_pdf_report(df: pd.DataFrame, state, title: str, analyst_name: str | None = None) -> bytes:
    """
    Generates a simple multi-page PDF:
      - Cover/summary
      - Event type bar
      - Touch heatmap
      - Pass map
      - Shot map
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 0.15 * inch))

    meta_lines = [
        f"<b>Opposition:</b> {state.opposition}",
        f"<b>Date range:</b> {state.date_start} to {state.date_end}",
        f"<b>Competitions:</b> {', '.join(state.competitions) if state.competitions else 'All'}",
        f"<b>Seasons:</b> {', '.join(state.seasons) if state.seasons else 'All'}",
        f"<b>Event types:</b> {', '.join(state.event_types[:12])}{'…' if len(state.event_types) > 12 else ''}",
    ]
    if analyst_name:
        meta_lines.insert(0, f"<b>Analyst:</b> {analyst_name}")

    for line in meta_lines:
        story.append(Paragraph(line, styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    # Basic metrics table
    metrics = [
        ["Events", f"{len(df):,}"],
        ["Matches", f"{df['Match'].nunique():,}"],
        ["Players", f"{df['Player'].nunique():,}"],
    ]
    if "Event type" in df.columns:
        metrics.append(["Top event type", str(df["Event type"].value_counts().index[0]) if len(df) else "-"])

    t = Table(metrics, colWidths=[2.2 * inch, 4.8 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(t)
    story.append(PageBreak())

    # Figures on their own pages
    figs = [
        ("Event Type Profile", fig_event_type_bar(df)),
        ("Touch Heatmap", fig_touch_heatmap(df)),
        ("Pass Map", fig_pass_map(df)),
        ("Shot Map", fig_shot_map(df)),
    ]

    for heading, fig in figs:
        story.append(Paragraph(heading, styles["Heading1"]))
        story.append(Spacer(1, 0.15 * inch))
        png = _fig_to_png_bytes(fig)
        img = Image(png, width=7.1 * inch, height=4.7 * inch)
        story.append(img)
        story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
