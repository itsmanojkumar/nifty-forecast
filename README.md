# Nifty sector forecasts

Time-series and ML forecasts of Nifty sector indices to Dec 2027, with a dashboard (`index.html`).

- `forecast.py` – 12 indices, walk-forward model selection, holdout check, exports `data.json`
- `metal_official.py` – Nifty Metal on official NSE daily data (`fetch_metal.py` downloads it)
- `defence_ml.py` – ML model for a defence-stock basket
- `template.html` / `index.html` – dashboard

## MLOps (MLflow)

`mlops/` tracks, evaluates, registers and serves the production forecaster (monthly trend + 80% band).

```bash
pip install mlflow pandas numpy scikit-learn matplotlib yfinance pytest
python -m pytest tests -q                         # unit tests
python -m mlops.train                             # backtest, log a run, register a model version, apply the promotion gate
python -m mlops.train --index "Nifty Metal"       # one index
python -m mlops.predict "Nifty Metal" 14          # forecast 14 months with the registered champion
mlflow ui --backend-store-uri sqlite:///mlflow.db # browse runs, metrics, artifacts and the model registry
```

What each run records: parameters (method, band, backtest window), the data window and a SHA-256 data fingerprint, the git commit,
backtest metrics at 1/3/6/12 months (MAPE vs "no change", 80% band coverage, direction vs always-up), the backtest table,
the forecast and a chart as artifacts, and the deployable model with an input/output signature.

**Promotion gate:** a new version becomes `champion` only if its 12-month error is no worse than "no change" and its 80% band covers at
least 75% of outcomes; otherwise it is tagged `challenger`. The gate checks the error, not whether the improvement is statistically
significant (it is not, see `stakeholder_evidence.json`).

Statistical exercise, not investment advice.
