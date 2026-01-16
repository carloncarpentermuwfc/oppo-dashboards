import os
import sys

# Ensure local modules (same folder as this file) are importable on Streamlit Cloud and similar runtimes
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import streamlit as st

from events_data import load_events, apply_filters, FilterState, available_date_bounds
from viz import (
    fig_event_type_bar,
    fig_touch_heatmap,
    fig_pass_map,
    fig_shot_map,
)
from report import build_pdf_report


st.set_page_config(page_title="Opposition Team-Season Dashboard", layout="wide")

st.title("Opposition Team-Season Dashboard")
st.caption("Filter by opposition + season + competition + date range. Export a PDF profile from the current filters.")

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload events CSV", type=["csv"])
    sample_path = st.text_input("...or local path (optional)", value="")
    load_btn = st.button("Load data", type="primary")

if "df" not in st.session_state:
    st.session_state.df = None

if load_btn:
    try:
        df = load_events(uploaded_file=uploaded, fallback_path=sample_path if sample_path.strip() else None)
        st.session_state.df = df
        st.success(f"Loaded {len(df):,} events.")
    except Exception as e:
        st.session_state.df = None
        st.error(f"Failed to load data: {e}")

df = st.session_state.df
if df is None:
    st.info("Upload your events CSV in the sidebar, then click **Load data**.")
    st.stop()

# ---- Filters ----
min_date, max_date = available_date_bounds(df)

with st.sidebar:
    st.header("Filters")

    opposition = st.selectbox("Opposition team", options=sorted(df["Team"].dropna().unique().tolist()))
    competitions = sorted(df["Competition"].dropna().unique().tolist())
    competition = st.multiselect("Competition", options=competitions, default=competitions)

    seasons = sorted(df["Season"].dropna().unique().tolist())
    season = st.multiselect("Season", options=seasons, default=seasons)

    date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

    event_types = sorted(df["Event type"].dropna().unique().tolist())
    event_type = st.multiselect("Event types", options=event_types, default=event_types)

    only_att_third = st.checkbox("Only events in attacking third (if available)", value=False)

state = FilterState(
    opposition=opposition,
    competitions=competition,
    seasons=season,
    date_start=date_range[0],
    date_end=date_range[1],
    event_types=event_type,
    only_attacking_third=only_att_third,
)

fdf = apply_filters(df, state)

# ---- Summary ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Events", f"{len(fdf):,}")
c2.metric("Matches", f"{fdf['Match'].nunique():,}")
c3.metric("Players", f"{fdf['Player'].nunique():,}")
c4.metric("Date span", f"{state.date_start} → {state.date_end}")

st.divider()

# ---- Visuals ----
left, right = st.columns(2, gap="large")

with left:
    st.subheader("Event Type Profile")
    st.pyplot(fig_event_type_bar(fdf), clear_figure=True)

    st.subheader("Touch Heatmap")
    st.pyplot(fig_touch_heatmap(fdf), clear_figure=True)

with right:
    st.subheader("Pass Map (completed vs incomplete)")
    st.pyplot(fig_pass_map(fdf), clear_figure=True)

    st.subheader("Shot Map")
    st.pyplot(fig_shot_map(fdf), clear_figure=True)

st.divider()

# ---- PDF Export ----
st.subheader("Export PDF report")

colA, colB = st.columns([1, 2])
with colA:
    report_title = st.text_input("Report title", value=f"{state.opposition} — Team-Season Profile")
    analyst_name = st.text_input("Analyst name (optional)", value="")
    export_btn = st.button("Generate PDF", type="primary")

with colB:
    st.caption("The PDF is generated from the current filters (including date range).")

if export_btn:
    try:
        pdf_bytes = build_pdf_report(
            df=fdf,
            state=state,
            title=report_title,
            analyst_name=analyst_name.strip() or None,
        )
        st.success("PDF generated.")
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"{state.opposition}_team_season_profile.pdf".replace(" ", "_"),
            mime="application/pdf",
        )
    except Exception as e:
        st.error(f"PDF generation failed: {e}")
