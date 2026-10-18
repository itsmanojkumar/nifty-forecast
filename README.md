# Nifty sector forecasts

Time-series and ML forecasts of Nifty sector indices to Dec 2027, with a dashboard (`index.html`).

- `forecast.py` – 12 indices, walk-forward model selection, holdout check, exports `data.json`
- `metal_official.py` – Nifty Metal on official NSE daily data (`fetch_metal.py` downloads it)
- `defence_ml.py` – ML model for a defence-stock basket
- `template.html` / `index.html` – dashboard

Statistical exercise, not investment advice.
