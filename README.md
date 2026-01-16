# Opposition Team-Season Profiles (Tracking dataset)

This version is adapted for the merged tracking/enriched dataset (294 columns) that includes:
- `team_shortname`, `match_id`
- `xthreat`, `xshot_player_possession_*`, `xloss_player_possession_*`
- Coordinates: `x_start`, `y_start`, `x_end`, `y_end` (meters, centered)

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Date range filtering

Your tracking CSV does **not** include match dates. To enable date-range filters, upload an additional CSV with:

- `match_id`
- `date` (YYYY-MM-DD)

The app will attach `match_date` and enable the date filter automatically.

## Opposition filter

The main selector is **Opposition**, driven by `team_shortname`.

