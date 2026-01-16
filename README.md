# Opposition Team-Season Profiles (Tracking dataset) — Fixed imports/columns

This build fixes a common Streamlit Cloud issue where column headers may include:
- leading BOM characters
- trailing spaces
- slightly different team shortname column naming

The loader now **auto-detects** and renames required columns to canonical names:
- `match_id`
- `team_id`
- `team_shortname`

## Date range filtering
Your tracking dataset doesn't include dates. Upload an optional metadata CSV with:
- `match_id`
- `date` (YYYY-MM-DD)

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
