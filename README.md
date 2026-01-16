# Opposition Team-Season Dashboard (Streamlit)

This dashboard:
- Loads an events CSV
- Filters by **opposition team**, season, competition, **date range**, event types
- Exports a **team-season profile PDF** based on the current filters

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes about imports (fix included)
- `data.py` has been renamed to `events_data.py` to avoid module name conflicts.
- `app.py` forces the app directory onto `sys.path` so local imports work on Streamlit Cloud.

## Expected CSV columns
Required:
- `Event type`, `Outcome`, `Player`, `Team`, `Competition`, `Season`, `Match`, `Date`

Optional but used when available:
- `Start X`, `Start Y`, `End X`, `End Y`
- `In attacking third` / `Inside attacking third`
