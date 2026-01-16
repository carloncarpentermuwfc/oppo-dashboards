import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def _pitch_axes(ax):
    # Basic 120x80 StatsBomb-like pitch
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 80)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    # Outline
    ax.plot([0, 120, 120, 0, 0], [0, 0, 80, 80, 0], linewidth=1)
    # Halfway line
    ax.plot([60, 60], [0, 80], linewidth=1)
    # Penalty areas
    ax.plot([102, 120, 120, 102], [18, 18, 62, 62], linewidth=1)
    ax.plot([0, 18, 18, 0], [18, 18, 62, 62], linewidth=1)


def fig_event_type_bar(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 4))
    counts = df["Event type"].value_counts().head(12)
    ax.bar(counts.index.astype(str), counts.values)
    ax.set_ylabel("Count")
    ax.set_title("Top Event Types (by volume)")
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    fig.tight_layout()
    return fig


def fig_touch_heatmap(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 4.6))
    _pitch_axes(ax)

    if "Start X" not in df.columns or "Start Y" not in df.columns:
        ax.text(60, 40, "No Start X/Start Y columns found", ha="center", va="center")
        return fig

    x = pd.to_numeric(df["Start X"], errors="coerce").dropna()
    y = pd.to_numeric(df.loc[x.index, "Start Y"], errors="coerce").dropna()

    if len(x) < 10:
        ax.text(60, 40, "Not enough location data for heatmap", ha="center", va="center")
        return fig

    # 2D histogram
    bins_x, bins_y = 24, 16
    H, xedges, yedges = np.histogram2d(x, y, bins=[bins_x, bins_y], range=[[0, 120], [0, 80]])
    ax.imshow(H.T, origin="lower", extent=[0, 120, 0, 80], alpha=0.75)
    ax.set_title("Touch / Action Heatmap (Start locations)")
    fig.tight_layout()
    return fig


def fig_pass_map(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 4.6))
    _pitch_axes(ax)

    if not all(c in df.columns for c in ["Start X", "Start Y", "End X", "End Y"]):
        ax.text(60, 40, "No Start/End coordinate columns found", ha="center", va="center")
        return fig

    passes = df[df["Event type"].str.lower() == "pass"].copy()
    if passes.empty:
        ax.text(60, 40, "No pass events in selection", ha="center", va="center")
        return fig

    # Completed vs not (Outcome contains 'complete' often)
    outcome = passes["Outcome"].astype(str).str.lower()
    completed = passes[outcome.str.contains("complete", na=False)]
    incomplete = passes[~outcome.str.contains("complete", na=False)]

    def draw(sub, alpha):
        sx = pd.to_numeric(sub["Start X"], errors="coerce")
        sy = pd.to_numeric(sub["Start Y"], errors="coerce")
        ex = pd.to_numeric(sub["End X"], errors="coerce")
        ey = pd.to_numeric(sub["End Y"], errors="coerce")
        mask = ~(sx.isna() | sy.isna() | ex.isna() | ey.isna())
        sx, sy, ex, ey = sx[mask], sy[mask], ex[mask], ey[mask]
        for a, b, c, d in zip(sx, sy, ex, ey):
            ax.arrow(a, b, c - a, d - b, length_includes_head=True, head_width=1.2, head_length=1.8, alpha=alpha, linewidth=0.7)

    draw(completed, alpha=0.35)
    draw(incomplete, alpha=0.12)

    ax.set_title("Pass map (darker = more likely completed)")
    fig.tight_layout()
    return fig


def fig_shot_map(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 4.6))
    _pitch_axes(ax)

    if "Start X" not in df.columns or "Start Y" not in df.columns:
        ax.text(60, 40, "No Start X/Start Y columns found", ha="center", va="center")
        return fig

    shots = df[df["Event type"].str.lower() == "shot"].copy()
    if shots.empty:
        ax.text(60, 40, "No shot events in selection", ha="center", va="center")
        return fig

    sx = pd.to_numeric(shots["Start X"], errors="coerce")
    sy = pd.to_numeric(shots["Start Y"], errors="coerce")
    mask = ~(sx.isna() | sy.isna())
    sx, sy = sx[mask], sy[mask]

    ax.scatter(sx, sy, alpha=0.6, s=20)
    ax.set_title("Shot locations (Start X/Y)")
    fig.tight_layout()
    return fig
