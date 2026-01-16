import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# Tracking-style pitch coordinates (meters), centered:
# x in [-52.5, 52.5], y in [-34, 34] (approx)
X_MIN, X_MAX = -52.5, 52.5
Y_MIN, Y_MAX = -34.0, 34.0


def _pitch_axes(ax):
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    # Outline
    ax.plot([X_MIN, X_MAX, X_MAX, X_MIN, X_MIN], [Y_MIN, Y_MIN, Y_MAX, Y_MAX, Y_MIN], linewidth=1)
    # Halfway
    ax.plot([0, 0], [Y_MIN, Y_MAX], linewidth=1)
    # Penalty areas (approx in meters, centered)
    # Length 16.5m, width 40.3m => y +-20.15
    pa_y = 20.15
    ax.plot([X_MAX-16.5, X_MAX, X_MAX, X_MAX-16.5], [-pa_y, -pa_y, pa_y, pa_y], linewidth=1)
    ax.plot([X_MIN, X_MIN+16.5, X_MIN+16.5, X_MIN], [-pa_y, -pa_y, pa_y, pa_y], linewidth=1)


def fig_possession_outcomes(df: pd.DataFrame):
    """
    Uses available possession flags + xloss/xshot maxima if present.
    """
    fig, ax = plt.subplots(figsize=(7, 4))

    if "team_possession_id" not in df.columns:
        ax.text(0.5, 0.5, "No team_possession_id column", ha="center", va="center", transform=ax.transAxes)
        return fig

    # Aggregate per possession
    g = df.groupby("team_possession_id", dropna=True)

    outcomes = []
    for pid, sub in g:
        xshot = sub["xshot_player_possession_max"].max() if "xshot_player_possession_max" in sub.columns else np.nan
        xloss = sub["xloss_player_possession_max"].max() if "xloss_player_possession_max" in sub.columns else np.nan
        # simple rule:
        if pd.notna(xshot) and xshot > 0:
            outcomes.append("Shot")
        elif pd.notna(xloss) and xloss > 0:
            outcomes.append("Turnover")
        else:
            outcomes.append("Other")

    s = pd.Series(outcomes).value_counts()
    ax.bar(s.index.astype(str), s.values)
    ax.set_title("Possession outcomes (heuristic)")
    ax.set_ylabel("Count")
    fig.tight_layout()
    return fig


def fig_xthreat_timeseries(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 4))

    if "xthreat" not in df.columns:
        ax.text(0.5, 0.5, "No xthreat column found", ha="center", va="center", transform=ax.transAxes)
        return fig

    # Create a continuous time axis in seconds (minute_start*60 + second_start)
    t = pd.to_numeric(df.get("minute_start"), errors="coerce").fillna(0) * 60 + pd.to_numeric(df.get("second_start"), errors="coerce").fillna(0)
    x = pd.to_numeric(df["xthreat"], errors="coerce").fillna(0)

    # Bin into 1-minute buckets for readability
    minute = (t // 60).astype(int)
    series = x.groupby(minute).sum()

    ax.plot(series.index.values, series.values)
    ax.set_title("xThreat created over match time (sum per minute)")
    ax.set_xlabel("Minute")
    ax.set_ylabel("xThreat (sum)")
    fig.tight_layout()
    return fig


def fig_threat_heatmap(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 4.6))
    _pitch_axes(ax)

    if "x_start" not in df.columns or "y_start" not in df.columns:
        ax.text(0, 0, "No x_start/y_start columns", ha="center", va="center")
        return fig

    x = pd.to_numeric(df["x_start"], errors="coerce")
    y = pd.to_numeric(df["y_start"], errors="coerce")
    w = pd.to_numeric(df["xthreat"], errors="coerce") if "xthreat" in df.columns else None

    mask = ~(x.isna() | y.isna())
    x, y = x[mask], y[mask]
    if w is not None:
        w = w[mask].fillna(0)

    if len(x) < 25:
        ax.text(0, 0, "Not enough location data", ha="center", va="center")
        return fig

    bins_x, bins_y = 30, 20
    if w is None:
        H, xedges, yedges = np.histogram2d(x, y, bins=[bins_x, bins_y], range=[[X_MIN, X_MAX], [Y_MIN, Y_MAX]])
    else:
        H, xedges, yedges = np.histogram2d(
            x, y, bins=[bins_x, bins_y], range=[[X_MIN, X_MAX], [Y_MIN, Y_MAX]], weights=w
        )

    ax.imshow(H.T, origin="lower", extent=[X_MIN, X_MAX, Y_MIN, Y_MAX], alpha=0.75)
    ax.set_title("Threat creation heatmap (weighted by xThreat when available)")
    fig.tight_layout()
    return fig


def fig_progression_map(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 4.6))
    _pitch_axes(ax)

    needed = {"x_start", "y_start", "x_end", "y_end"}
    if not needed.issubset(set(df.columns)):
        ax.text(0, 0, "No x_start/y_start/x_end/y_end columns", ha="center", va="center")
        return fig

    sub = df.copy()
    sx = pd.to_numeric(sub["x_start"], errors="coerce")
    sy = pd.to_numeric(sub["y_start"], errors="coerce")
    ex = pd.to_numeric(sub["x_end"], errors="coerce")
    ey = pd.to_numeric(sub["y_end"], errors="coerce")

    mask = ~(sx.isna() | sy.isna() | ex.isna() | ey.isna())
    sx, sy, ex, ey = sx[mask], sy[mask], ex[mask], ey[mask]

    if len(sx) < 25:
        ax.text(0, 0, "Not enough progression vectors", ha="center", va="center")
        return fig

    # Sample for speed
    if len(sx) > 1500:
        idx = np.random.choice(len(sx), size=1500, replace=False)
        sx, sy, ex, ey = sx.iloc[idx], sy.iloc[idx], ex.iloc[idx], ey.iloc[idx]

    for a, b, c, d in zip(sx, sy, ex, ey):
        ax.arrow(a, b, c - a, d - b, length_includes_head=True, head_width=0.7, head_length=1.0, alpha=0.12, linewidth=0.6)

    ax.set_title("Progression vectors (start → end)")
    fig.tight_layout()
    return fig
