from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd
import re


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
    return df


def _find_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    cols = list(df.columns)
    lower_map = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def _find_fuzzy(df: pd.DataFrame, pattern: str) -> Optional[str]:
    for c in df.columns:
        if re.search(pattern, str(c), flags=re.IGNORECASE):
            return c
    return None


@dataclass(frozen=True)
class FilterState:
    team: str
    opponents: list[str]
    match_ids: list[int]
    date_start: Optional[date]
    date_end: Optional[date]
    phases: list[str]
    only_possession_starts: bool = False
    only_possession_ends: bool = False
    has_dates: bool = False


def load_tracking_events(uploaded_file=None, fallback_path: Optional[str] = None) -> pd.DataFrame:
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file, comment="#")
    elif fallback_path:
        df = pd.read_csv(fallback_path, comment="#")
    else:
        raise ValueError("No file provided. Upload the CSV or provide a local path.")

    df = _normalize_columns(df)

    match_col = _find_column(df, ["match_id"]) or _find_fuzzy(df, r"^match[\s_]*id$")
    teamid_col = _find_column(df, ["team_id"]) or _find_fuzzy(df, r"^team[\s_]*id$")
    short_col = (
        _find_column(df, ["team_shortname", "team_short_name", "team_short", "team_abbrev", "team_abbreviation"])
        or _find_fuzzy(df, r"team.*short")
        or _find_fuzzy(df, r"team.*abbr")
        or _find_fuzzy(df, r"team.*name")
    )

    missing = []
    if match_col is None: missing.append("match_id")
    if teamid_col is None: missing.append("team_id")
    if short_col is None: missing.append("team_shortname")
    if missing:
        raise ValueError(
            "Could not find required columns: " + ", ".join(missing) +
            ". First 30 detected columns: " + ", ".join(list(df.columns)[:30])
        )

    df = df.rename(columns={match_col: "match_id", teamid_col: "team_id", short_col: "team_shortname"})

    df["match_id"] = pd.to_numeric(df["match_id"], errors="coerce").astype("Int64")
    df["team_id"] = pd.to_numeric(df["team_id"], errors="coerce").astype("Int64")
    df["team_shortname"] = df["team_shortname"].astype(str).str.strip()

    for c in ["minute_start", "second_start"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = 0

    if "team_possession_id" in df.columns:
        df["team_possession_id"] = pd.to_numeric(df["team_possession_id"], errors="coerce").astype("Int64")

    for c in ["xthreat", "player_targeted_xthreat", "xloss_player_possession_max", "xshot_player_possession_max"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    for c in ["x_start", "y_start", "x_end", "y_end"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "team_in_possession_phase_type" in df.columns:
        df["team_in_possession_phase_type"] = df["team_in_possession_phase_type"].astype(str)

    for c in ["is_team_possession_start", "is_team_possession_end"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.lower().map(
                {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False}
            )

    return df


def load_match_metadata(uploaded_file) -> Optional[pd.DataFrame]:
    if uploaded_file is None:
        return None
    meta = pd.read_csv(uploaded_file)
    meta.columns = [str(c).strip().lstrip("\ufeff") for c in meta.columns]
    if not {"match_id", "date"}.issubset(set(meta.columns)):
        raise ValueError("Match metadata CSV must have columns: match_id, date")
    meta = meta.copy()
    meta["match_id"] = pd.to_numeric(meta["match_id"], errors="coerce").astype("Int64")
    meta["date"] = pd.to_datetime(meta["date"], errors="coerce").dt.date
    meta = meta.dropna(subset=["match_id", "date"])
    return meta


def attach_match_dates(df: pd.DataFrame, meta: Optional[pd.DataFrame]):
    if meta is None:
        return df, False
    out = df.merge(meta[["match_id", "date"]], on="match_id", how="left").rename(columns={"date": "match_date"})
    return out, out["match_date"].notna().any()


def add_opponent_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds opponent_shortname for each (match_id, team_shortname).
    Assumes typical football matches have two teams per match_id.
    If more than two teams appear, uses the most frequent 'other team' as opponent.
    """
    out = df.copy()

    # Map match_id -> list of teams
    teams_by_match = out.groupby("match_id")["team_shortname"].apply(lambda s: [t for t in s.dropna().unique().tolist()]).to_dict()

    def opponent_for_row(row):
        mid = row["match_id"]
        team = row["team_shortname"]
        teams = teams_by_match.get(mid, [])
        others = [t for t in teams if t != team]
        if not others:
            return None
        if len(others) == 1:
            return others[0]
        # if >1, pick most frequent other team in that match
        sub = out[out["match_id"] == mid]
        freq = sub[sub["team_shortname"] != team]["team_shortname"].value_counts()
        return freq.index[0] if len(freq) else others[0]

    out["opponent_shortname"] = out.apply(opponent_for_row, axis=1)
    return out


def available_date_bounds(df: pd.DataFrame):
    return df["match_date"].min(), df["match_date"].max()


def available_match_bounds(df: pd.DataFrame):
    mmin = df["match_id"].dropna().min()
    mmax = df["match_id"].dropna().max()
    return int(mmin), int(mmax)


def apply_filters(df: pd.DataFrame, state: FilterState) -> pd.DataFrame:
    f = df.copy()
    f = f[f["team_shortname"] == state.team]

    if state.opponents:
        if "opponent_shortname" in f.columns:
            f = f[f["opponent_shortname"].isin(state.opponents)]

    if state.match_ids:
        f = f[f["match_id"].isin(state.match_ids)]

    if state.phases and "team_in_possession_phase_type" in f.columns:
        f = f[f["team_in_possession_phase_type"].isin(state.phases)]

    if state.only_possession_starts and "is_team_possession_start" in f.columns:
        f = f[f["is_team_possession_start"] == True]

    if state.only_possession_ends and "is_team_possession_end" in f.columns:
        f = f[f["is_team_possession_end"] == True]

    if state.has_dates and "match_date" in f.columns and state.date_start and state.date_end:
        f = f[(f["match_date"] >= state.date_start) & (f["match_date"] <= state.date_end)]

    return f.reset_index(drop=True)
