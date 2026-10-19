"""Rolling-origin backtest of the production trend model against 'no change' (last 72 months, 1/3/6/12-month horizons)."""
import numpy as np
import pandas as pd
from .forecaster import trend_path, band_width


def backtest(y: pd.Series, windows: int = 72, horizons=(1, 3, 6, 12)):
    metrics, rows = {}, []
    for H in horizons:
        rec = []
        for i in range(len(y) - windows, len(y) - H):
            tr = y.iloc[:i + 1].values; actual = y.iloc[i + H]; last = tr[-1]
            p, k = trend_path(tr, H)[-1], band_width(tr, H)[-1]
            rec.append(dict(horizon=H, origin=y.index[i].strftime("%Y-%m"), target=y.index[i + H].strftime("%Y-%m"),
                            err_trend=abs(np.exp(p - actual) - 1) * 100, err_naive=abs(np.exp(last - actual) - 1) * 100,
                            inside=bool(p - k <= actual <= p + k), hit=bool(np.sign(p - last) == np.sign(actual - last)), up=bool(actual > last)))
        R = pd.DataFrame(rec); rows.append(R)
        metrics.update({f"mape_{H}m_trend": R.err_trend.mean(), f"mape_{H}m_naive": R.err_naive.mean(),
                        f"improvement_{H}m_pct": (1 - R.err_trend.mean() / R.err_naive.mean()) * 100,
                        f"coverage80_{H}m_pct": R.inside.mean() * 100, f"direction_{H}m_pct": R.hit.mean() * 100,
                        f"base_up_{H}m_pct": R.up.mean() * 100})
    return {k: round(float(v), 3) for k, v in metrics.items()}, pd.concat(rows, ignore_index=True)


def gate(m: dict):
    """Promotion gate for the 'champion' alias: must not be worse than 'no change' at 12 months, and the 80% band must be honest
    (cover at least 75% of outcomes)."""
    checks = {"beats_naive_12m": bool(m["improvement_12m_pct"] >= 0), "band_coverage_ok": bool(m["coverage80_12m_pct"] >= 75)}
    return all(checks.values()), checks
