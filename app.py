import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import streamlit as st

from tracking_data import (
    load_tracking_events,
    load_match_metadata,
    attach_match_dates,
    add_opponent_labels,
    FilterState,
    available_date_bounds,
    available_match_bounds,
    apply_filters,
)
from viz import (
    fig_possession_outcomes,
    fig_xthreat_timeseries,
    fig_threat_heatmap,
    fig_progression_map,
)
from report import build_pdf_report

st.set_page_config(page_title="Team Season Profiles (Tracking)", layout="wide")

st.title("Team Season Profiles")
st.caption(
    "Select a focus team. Dashboards and PDFs summarize that team across ALL opponents "
    "(optionally filter opponents and date ranges)."
)

# ---------------- Data load ----------------
with st.sidebar:
    st.header("Data")
    uploaded_events = st.file_uploader("Upload main tracking CSV", type=["csv"])
    local_path = st.text_input("...or local path (optional)", value="")
    uploaded_meta = st.file_uploader("Optional: match metadata CSV (match_id, date)", type=["csv"])
    load_btn = st.button("Load data", type="primary")

if "df" not in st.session_state:
    st.session_state.df = None
if "has_dates" not in st.session_state:
    st.session_state.has_dates = False

if load_btn:
    try:
        df = load_tracking_events(uploaded_file=uploaded_events, fallback_path=local_path.strip() or None)
        meta = load_match_metadata(uploaded_meta) if uploaded_meta is not None else None
        df, has_dates = attach_match_dates(df, meta)
        df = add_opponent_labels(df)  # adds opponent_shortname per match/team
        st.session_state.df = df
        st.session_state.has_dates = has_dates
        st.success(f"Loaded {len(df):,} rows. Dates available: {'Yes' if has_dates else 'No'}")
    except Exception as e:
        st.session_state.df = None
        st.session_state.has_dates = False
        st.error(f"Failed to load: {e}")

df = st.session_state.df
if df is None:
    st.info("Upload the tracking CSV in the sidebar and click **Load data**.")
    st.stop()

has_dates = st.session_state.has_dates

# ---------------- Filters ----------------
with st.sidebar:
    st.header("Filters")

    teams = sorted(df["team_shortname"].dropna().unique().tolist())
    team = st.selectbox("Focus team", options=teams)

    # Opponent filter (default: all)
    opps = sorted(df.loc[df["team_shortname"] == team, "opponent_shortname"].dropna().unique().tolist())
    opponents = st.multiselect("Opponents (optional)", options=opps, default=opps)

    # Match selection (default: all matches for selected opponents)
    match_ids = sorted(
        df.loc[(df["team_shortname"] == team) & (df["opponent_shortname"].isin(opponents)), "match_id"]
        .dropna()
        .unique()
        .tolist()
    )
    selected_matches = st.multiselect("Matches (match_id)", options=match_ids, default=match_ids)

    # Date range (default: full range)
    if has_dates:
        dmin, dmax = available_date_bounds(df)
        date_range = st.date_input("Date range", value=(dmin, dmax), min_value=dmin, max_value=dmax)
        date_start, date_end = date_range
    else:
        st.caption("No match dates found. Upload match metadata CSV to enable date ranges.")
        mmin, mmax = available_match_bounds(df)
        _ = st.slider("Match ID range (fallback)", min_value=int(mmin), max_value=int(mmax), value=(int(mmin), int(mmax)))
        date_start, date_end = None, None

    phase_opts = sorted(df["team_in_possession_phase_type"].dropna().unique().tolist()) if "team_in_possession_phase_type" in df.columns else []
    phases = st.multiselect("In-possession phase", options=phase_opts, default=phase_opts)

    only_possession_starts = st.checkbox("Only possession starts", value=False)
    only_possession_ends = st.checkbox("Only possession ends", value=False)

state = FilterState(
    team=team,
    opponents=opponents,
    match_ids=selected_matches,
    date_start=date_start,
    date_end=date_end,
    phases=phases,
    only_possession_starts=only_possession_starts,
    only_possession_ends=only_possession_ends,
    has_dates=has_dates,
)

fdf = apply_filters(df, state)

# ---------------- Summary ----------------
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Team", state.team)
c2.metric("Matches", f"{fdf['match_id'].nunique():,}")
c3.metric("Opponents", f"{fdf['opponent_shortname'].nunique():,}" if "opponent_shortname" in fdf.columns else "—")
c4.metric("Possessions (approx)", f"{fdf['team_possession_id'].nunique():,}" if "team_possession_id" in fdf.columns else "—")
c5.metric("Total xThreat", f"{fdf['xthreat'].fillna(0).sum():.2f}" if "xthreat" in fdf.columns else "—")

st.divider()

# ---------------- Visuals ----------------
left, right = st.columns(2, gap="large")

with left:
    st.subheader(f"{state.team}: Possession outcomes")
    st.pyplot(fig_possession_outcomes(fdf), clear_figure=True)

    st.subheader(f"{state.team}: Threat creation heatmap")
    st.pyplot(fig_threat_heatmap(fdf), clear_figure=True)

with right:
    st.subheader(f"{state.team}: xThreat over time")
    st.pyplot(fig_xthreat_timeseries(fdf), clear_figure=True)

    st.subheader(f"{state.team}: Progression map (start → end)")
    st.pyplot(fig_progression_map(fdf), clear_figure=True)

st.divider()

# ---------------- PDF Export ----------------
st.subheader("Export PDF profile")

colA, colB = st.columns([1, 2])
with colA:
    report_title = st.text_input("Report title", value=f"{state.team} — Team Profile (All Opponents)")
    analyst = st.text_input("Analyst name (optional)", value="")
    export_btn = st.button("Generate PDF", type="primary")

with colB:
    st.caption("PDF is generated from the current filters (team + opponents + matches + dates).")

if export_btn:
    try:
        pdf_bytes = build_pdf_report(
            df=fdf,
            state=state,
            title=report_title,
            analyst_name=analyst.strip() or None,
        )
        st.success("PDF generated.")
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"{state.team}_team_profile.pdf".replace(" ", "_"),
            mime="application/pdf",
        )
    except Exception as e:
        st.error(f"PDF generation failed: {e}")
