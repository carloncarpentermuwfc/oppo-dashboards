from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Iterable

import pandas as pd


REQUIRED_COLS = [
    "Event type",
    "Outcome",
    "Player",
    "Team",
    "Competition",
    "Season",
    "Match",
    "Date",
]

OPTIONAL_BOOL_COLS = [
    "In attacking third",
    "In attacking half",
    "Inside attacking third",
    "Inside attacking half",
]

COORD_COLS = ["Start X", "Start Y", "End X", "End Y"]


@dataclass(frozen=True)
class FilterState:
    opposition: str
    competitions: list[str]
    seasons: list[str]
    date_start: date
    date_end: date
    event_types: list[str]
    only_attacking_third: bool = False


def load_events(uploaded_file=None, fallback_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load events from a Streamlit UploadedFile OR a local path.

    - Parses Date to datetime.date
    - Ensures expected columns exist
    """
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    elif fallback_path:
        df = pd.read_csv(fallback_path)
    else:
        raise ValueError("No file provided. Upload a CSV or provide a fallback path.")

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Parse date
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    if df["Date"].isna().all():
        raise ValueError("Could not parse any dates from the 'Date' column.")

    # Normalize outcomes and event types
    df["Event type"] = df["Event type"].astype(str)
    df["Outcome"] = df["Outcome"].astype(str)
    df["Player"] = df["Player"].astype(str)
    df["Team"] = df["Team"].astype(str)
    df["Competition"] = df["Competition"].astype(str)
    df["Season"] = df["Season"].astype(str)
    df["Match"] = df["Match"].astype(str)

    # Coerce optional bool cols if they exist
    for c in OPTIONAL_BOOL_COLS:
        if c in df.columns:
            # Accept True/False, 0/1, yes/no etc.
            df[c] = df[c].astype(str).str.lower().map(
                {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False}
            ).fillna(False)

    # Coerce coordinates if present
    for c in COORD_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def available_date_bounds(df: pd.DataFrame):
    dmin = df["Date"].min()
    dmax = df["Date"].max()
    return dmin, dmax


def apply_filters(df: pd.DataFrame, state: FilterState) -> pd.DataFrame:
    fdf = df.copy()

    fdf = fdf[fdf["Team"] == state.opposition]
    if state.competitions:
        fdf = fdf[fdf["Competition"].isin(state.competitions)]
    if state.seasons:
        fdf = fdf[fdf["Season"].isin(state.seasons)]
    if state.event_types:
        fdf = fdf[fdf["Event type"].isin(state.event_types)]

    fdf = fdf[(fdf["Date"] >= state.date_start) & (fdf["Date"] <= state.date_end)]

    if state.only_attacking_third:
        col = None
        for candidate in ["In attacking third", "Inside attacking third"]:
            if candidate in fdf.columns:
                col = candidate
                break
        if col:
            fdf = fdf[fdf[col] == True]

    return fdf.reset_index(drop=True)
