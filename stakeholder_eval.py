"""Evidence pack for stakeholders: does the forecast work? Writes stakeholder_evidence.json.

1. Production model (monthly trend + 80% band): rolling-origin backtest over the last 72 months at 1/3/6/12-month horizons,
   against "no change", with band coverage and a Diebold-Mariano test using Newey-West (HAC) errors.
2. ML challengers (Ridge, random forest, tuned boosting, GRU, ensemble) on daily data, 21-day horizon, purged walk-forward
   (from ml_pipeline.run), scored against the trend baseline with the same HAC test.
3. Forecast to Dec 2027 from the production model.
"""
import warnings; warnings.filterwarnings("ignore")
import json, numpy as np, pandas as pd, yfinance as yf
from scipy import stats
from ml_pipeline import run as run_ml

Z80 = 1.2816

def load_daily(name):
    if name == "Nifty Metal":
        return pd.read_csv("nifty_metal_official.csv", parse_dates=["date"]).set_index("date")["close"]
    return yf.download("^NSEI", start="2007-09-01", auto_adjust=True, progress=False)["Close"].squeeze().dropna()

def dm_pvalue(d, lag):
    """Two-sided Diebold-Mariano p-value for mean(d) = 0, Newey-West variance with `lag` lags (overlapping targets)."""
    d = np.asarray(d, float); n = len(d); u = d - d.mean()
    if np.allclose(u, 0): return None
    v = u @ u / n
    for k in range(1, lag + 1):
        v += 2 * (1 - k / (lag + 1)) * (u[k:] @ u[:-k]) / n
    t = d.mean() / np.sqrt(v / n)
    return round(float(2 * stats.t.sf(abs(t), n - 1)), 4)

def trend(tr, H):
    return tr.iloc[-1] + (tr.iloc[-1] - tr.iloc[0]) / (len(tr) - 1) * np.arange(1, H + 1)

def band(tr, H):
    return np.sqrt(np.arange(1, H + 1)) * tr.diff().dropna().values[-60:].std() * Z80

def production_backtest(y):
    out = {}
    for H in (1, 3, 6, 12):
        rec = []
        for i in range(len(y) - 72, len(y) - H):
            tr = y.iloc[:i + 1]; a = y.iloc[i + H]; b = tr.iloc[-1]
            p = trend(tr, H)[-1]; k = band(tr, H)[-1]
            rec.append(dict(origin=y.index[i].strftime("%Y-%m"), target=y.index[i + H].strftime("%Y-%m"),
                            pred=float(np.exp(p)), lo=float(np.exp(p - k)), hi=float(np.exp(p + k)), actual=float(np.exp(a)), start=float(np.exp(b)),
                            err_trend=abs(np.exp(p - a) - 1) * 100, err_naive=abs(np.exp(b - a) - 1) * 100,
                            hit=bool(np.sign(p - b) == np.sign(a - b)), up=bool(a > b), inside=bool(p - k <= a <= p + k)))
        R = pd.DataFrame(rec)
        out[H] = dict(n=len(R), mape_trend=round(R.err_trend.mean(), 2), mape_naive=round(R.err_naive.mean(), 2),
                      improvement_pct=round((1 - R.err_trend.mean() / R.err_naive.mean()) * 100, 1),
                      win_rate=round(float((R.err_trend < R.err_naive).mean() * 100), 1),
                      direction=round(R.hit.mean() * 100, 1), base_up=round(R.up.mean() * 100, 1),
                      coverage80=round(R.inside.mean() * 100, 1), p_vs_naive=dm_pvalue(R.err_trend - R.err_naive, H - 1),
                      series=[{k: (round(v, 1) if isinstance(v, float) else v) for k, v in r.items()} for r in rec])
    return out

def ml_challengers(name):
    m = run_ml(name); A = m["actual"]; P = m["pred"]; base = (P["Trend"] - A) ** 2; rows = []
    for k, v in P.items():
        se = (v - A) ** 2
        rows.append(dict(model=k, rmse_pct=round(float(np.sqrt(se.mean()) * 100), 2),
                         skill_vs_trend_pct=round(float((1 - se.mean() / base.mean()) * 100), 1),
                         direction=None if k == "No change" else round(float((np.sign(v) == np.sign(A)).mean() * 100), 1),
                         corr=round(float(np.corrcoef(v, A)[0, 1]), 3) if v.std() > 0 else None,
                         p_vs_trend=dm_pvalue(se - base, 20)))
    best = max((r for r in rows if r["model"] not in ("Trend", "No change")), key=lambda r: r["skill_vs_trend_pct"])
    step = 3
    scatter = [[round(float(p) * 100, 2), round(float(a) * 100, 2)] for p, a in zip(P[best["model"]][::step], A[::step])]
    return dict(test_days=m["test_days"], first=m["dates"][0], last=m["dates"][-1], up_share=round(float((A > 0).mean() * 100), 1),
                table=rows, best=best["model"], scatter=scatter)

def forecast(y, daily):
    H = (2027 - y.index[-1].year) * 12 + 12 - y.index[-1].month
    p = trend(y, H); k = band(y, H); fd = pd.date_range(y.index[-1], periods=H + 1, freq="M")[1:]
    return dict(asof=daily.index[-1].strftime("%d %b %Y"), current=round(float(daily.iloc[-1]), 1),
                hist=[[i.strftime("%Y-%m"), round(float(np.exp(v)), 1)] for i, v in y.items()],
                fc=[[i.strftime("%Y-%m"), round(float(np.exp(a)), 1), round(float(np.exp(a - b)), 1), round(float(np.exp(a + b)), 1)] for i, a, b in zip(fd, p, k)])

out = {}
for name in ("Nifty Metal", "Nifty 50"):
    daily = load_daily(name); y = np.log(daily.resample("M").last())
    out[name] = dict(source="Official NSE daily index file" if name == "Nifty Metal" else "Yahoo Finance (^NSEI)",
                     first=daily.index[0].strftime("%b %Y"), daily_rows=len(daily), months=len(y),
                     production=production_backtest(y), ml=ml_challengers(name), forecast=forecast(y, daily))
    pr = out[name]["production"]
    print(f"\n=== {name}")
    for H, r in pr.items():
        print(f"{H:>2}m  trend {r['mape_trend']:5.2f}%  naive {r['mape_naive']:5.2f}%  better {r['improvement_pct']:5.1f}%  win {r['win_rate']}%  "
              f"dir {r['direction']}% (up base {r['base_up']}%)  cover80 {r['coverage80']}%  p {r['p_vs_naive']}  n {r['n']}")
    print(pd.DataFrame(out[name]["ml"]["table"]).to_string(index=False)); print("best ML:", out[name]["ml"]["best"])
    f = out[name]["forecast"]["fc"][-1]; print("Dec 2027:", f)
json.dump(out, open("stakeholder_evidence.json", "w"))
print("\nwrote stakeholder_evidence.json")
from export_evidence import export
export()
