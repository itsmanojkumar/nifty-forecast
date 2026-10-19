"""Train, evaluate, log and register the forecasters with MLflow.

    python -m mlops.train                       # both indices
    python -m mlops.train --index "Nifty Metal"
    mlflow ui --backend-store-uri sqlite:///mlflow.db     # browse runs and the model registry
"""
import argparse, json, subprocess, tempfile
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow, mlflow.pyfunc, numpy as np, pandas as pd
from mlflow import MlflowClient
from mlflow.models import infer_signature
from .backtest import backtest, gate
from .data import INDICES, fingerprint, load_daily, monthly_log
from .forecaster import TrendForecaster

TRACKING_URI = "sqlite:///mlflow.db"


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def train_one(name: str) -> dict:
    registered = INDICES[name]
    daily = load_daily(name); y = monthly_log(daily)
    metrics, bt = backtest(y); ok, checks = gate(metrics)
    model = TrendForecaster([i.strftime("%Y-%m") for i in y.index], [float(v) for v in y.values])
    example = pd.DataFrame({"horizon_months": [14]}); out = model.predict(None, example)

    with mlflow.start_run(run_name=f"{name} trend {daily.index[-1]:%Y-%m-%d}") as run:
        mlflow.set_tags({"index": name, "git_sha": git_sha(), "data_fingerprint": fingerprint(daily), "gate_passed": str(ok)})
        mlflow.log_params({"model": "monthly log-price trend", "band": "80% (z=1.2816), sqrt-horizon", "band_window_months": 60,
                           "backtest_windows_months": 72, "data_rows_daily": len(daily), "data_rows_monthly": len(y),
                           "data_start": str(daily.index[0].date()), "data_end": str(daily.index[-1].date())})
        mlflow.log_metrics(metrics)
        mlflow.log_metrics({f"gate_{k}": float(v) for k, v in checks.items()})
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); bt.to_csv(d / "backtest.csv", index=False); out.to_csv(d / "forecast.csv", index=False)
            (d / "gate.json").write_text(json.dumps({"passed": ok, "checks": checks}, indent=1))
            fig, ax = plt.subplots(figsize=(8, 4)); ax.plot(np.exp(y.values[-96:]), c="k", label="actual")
            ax.plot(range(95, 95 + len(out) + 1), [np.exp(y.values[-1]), *out.forecast], c="C0", label="forecast")
            ax.fill_between(range(96, 96 + len(out)), out.p10, out.p90, alpha=.2); ax.set_title(f"{name}: forecast"); ax.legend()
            fig.savefig(d / "forecast.png", dpi=100); plt.close(fig)
            mlflow.log_artifacts(str(d), "evaluation")
        info = mlflow.pyfunc.log_model(name="model", python_model=model, signature=infer_signature(example, out), input_example=example,
                                       pip_requirements=["numpy", "pandas", f"mlflow=={mlflow.__version__}"],
                                       code_paths=[str(Path(__file__).parent)], registered_model_name=registered)
    client = MlflowClient(); version = str(info.registered_model_version)
    client.set_model_version_tag(registered, version, "gate_passed", str(ok))
    client.set_registered_model_alias(registered, "champion" if ok else "challenger", version)
    print(f"{name}: run {run.info.run_id[:8]}  v{version} -> {'champion' if ok else 'challenger'}  gate={checks}")
    print(f"   12m MAPE trend {metrics['mape_12m_trend']}% vs naive {metrics['mape_12m_naive']}%  coverage80 {metrics['coverage80_12m_pct']}%")
    return {"index": name, "version": version, "passed": ok, **metrics}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--index", choices=[*INDICES, "all"], default="all"); a = ap.parse_args()
    mlflow.set_tracking_uri(TRACKING_URI); mlflow.set_experiment("nifty-forecast")
    for n in (INDICES if a.index == "all" else [a.index]):
        train_one(n)
