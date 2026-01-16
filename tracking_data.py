from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd


REQUIRED = ["match_id", "team_id", "team_shortname", "minute_start", "second_start"]
OPTIONAL_DATE_COL = "match_date"


@dataclass(frozen=True)
class FilterState:
    opposition: str
    match_ids: list[int]
    date_start: Optional[date]
    date_end: Optional[date]
    phases: list[str]
    only_possession_starts: bool = False
    only_possession_ends: bool = False
    has_dates: bool = False


def load_tracking_events(uploaded_file=None, fallback_path: Optional[str] = None) -> pd.DataFrame:
    # merge-csv.com exports often start with commented lines; ignore them
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file, comment="#")
    elif fallback_path:
        df = pd.read_csv(fallback_path, comment="#")
    else:
        raise ValueError("No file provided. Upload the CSV or provide a local path.")

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Normalize types
    df["match_id"] = pd.to_numeric(df["match_id"], errors="coerce").astype("Int64")
    df["team_id"] = pd.to_numeric(df["team_id"], errors="coerce").astype("Int64")
    df["team_shortname"] = df["team_shortname"].astype(str)

    # Time fields
    df["minute_start"] = pd.to_numeric(df["minute_start"], errors="coerce")
    df["second_start"] = pd.to_numeric(df["second_start"], errors="coerce")

    # Helpful IDs if present
    if "team_possession_id" in df.columns:
        df["team_possession_id"] = pd.to_numeric(df["team_possession_id"], errors="coerce").astype("Int64")

    # Metrics
    for c in ["xthreat", "player_targeted_xthreat", "xloss_player_possession_max", "xshot_player_possession_max"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Coordinates (centered pitch in meters typically: x ~ [-52.5, 52.5], y ~ [-34, 34])
    for c in ["x_start", "y_start", "x_end", "y_end"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Phase type fields
    if "team_in_possession_phase_type" in df.columns:
        df["team_in_possession_phase_type"] = df["team_in_possession_phase_type"].astype(str)

    # Possession boundary flags
    for c in ["is_team_possession_start", "is_team_possession_end"]:
        if c in df.columns:
            # handle bool-ish data
            df[c] = df[c].astype(str).str.lower().map(
                {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False}
            )

    return df


def load_match_metadata(uploaded_file) -> Optional[pd.DataFrame]:
    """
    Optional CSV with columns:
      - match_id
      - date (YYYY-MM-DD)
    """
    if uploaded_file is None:
        return None
    meta = pd.read_csv(uploaded_file)
    expected = {"match_id", "date"}
    if not expected.issubset(set(meta.columns)):
        raise ValueError("Match metadata CSV must have columns: match_id, date")
    meta = meta.copy()
    meta["match_id"] = pd.to_numeric(meta["match_id"], errors="coerce").astype("Int64")
    meta["date"] = pd.to_datetime(meta["date"], errors="coerce").dt.date
    meta = meta.dropna(subset=["match_id", "date"])
    return meta


def attach_match_dates(df: pd.DataFrame, meta: Optional[pd.DataFrame]):
    """
    Adds df['match_date'] if metadata is provided.
    Returns (df, has_dates: bool)
    """
    if meta is None:
        return df, False

    out = df.merge(meta[["match_id", "date"]], on="match_id", how="left")
    out = out.rename(columns={"date": OPTIONAL_DATE_COL})
    has_dates = out[OPTIONAL_DATE_COL].notna().any()
    return out, has_dates


def available_date_bounds(df: pd.DataFrame):
    if OPTIONAL_DATE_COL not in df.columns:
        raise ValueError("No match_date column available.")
    dmin = df[OPTIONAL_DATE_COL].min()
    dmax = df[OPTIONAL_DATE_COL].max()
    return dmin, dmax


def available_match_bounds(df: pd.DataFrame):
    mmin = df["match_id"].dropna().min()
    mmax = df["match_id"].dropna().max()
    return int(mmin), int(mmax)


def apply_filters(df: pd.DataFrame, state: FilterState) -> pd.DataFrame:
    f = df.copy()
    f = f[f["team_shortname"] == state.opposition]

    if state.match_ids:
        f = f[f["match_id"].isin(state.match_ids)]

    if state.phases and "team_in_possession_phase_type" in f.columns:
        f = f[f["team_in_possession_phase_type"].isin(state.phases)]

    if state.only_possession_starts and "is_team_possession_start" in f.columns:
        f = f[f["is_team_possession_start"] == True]

    if state.only_possession_ends and "is_team_possession_end" in f.columns:
        f = f[f["is_team_possession_end"] == True]

    if state.has_dates and OPTIONAL_DATE_COL in f.columns and state.date_start and state.date_end:
        f = f[(f[OPTIONAL_DATE_COL] >= state.date_start) & (f[OPTIONAL_DATE_COL] <= state.date_end)]

    # Clean index
    return f.reset_index(drop=True)
