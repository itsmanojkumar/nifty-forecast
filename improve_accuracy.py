"""Can the production trend forecast be made more accurate? Honest protocol:

- candidates are chosen on DEV origins (everything before the dashboard's 72-month test window),
- then reported on the TEST window (the same last 72 month-ends the dashboard shows), never tuned there.

Point candidates (monthly log index): no change, trend (current), trend on a 5y / 10y window, trend+no-change blend,
trend-reversion (log index = line + AR(1) deviation from that line), and a trend/reversion blend.
Range candidates: current Gaussian band (60-month vol x sqrt(h)) vs. conformal band (quantiles of the method's own
past h-step errors, known at the origin). Interval score = Winkler score at 80% (lower is better).
"""
import warnings; warnings.filterwarnings("ignore")
import json, numpy as np, pandas as pd, yfinance as yf
from scipy import stats

def dm_pvalue(d, lag):
    """Two-sided Diebold-Mariano p-value, Newey-West variance (same test as stakeholder_eval.py)."""
    d = np.asarray(d, float); n = len(d); u = d - d.mean()
    if np.allclose(u, 0): return None
    v = u @ u / n
    for k in range(1, lag + 1): v += 2 * (1 - k / (lag + 1)) * (u[k:] @ u[:-k]) / n
    return round(float(2 * stats.t.sf(abs(d.mean() / np.sqrt(v / n)), n - 1)), 4)

Z80, ALPHA, MIN_TRAIN, MIN_ERRS = 1.2816, 0.2, 60, 24

def monthly(name):
    if name == "Nifty Metal":
        d = pd.read_csv("nifty_metal_official.csv", parse_dates=["date"]).set_index("date")["close"]
    else:
        d = yf.download("^NSEI", start="2007-09-01", auto_adjust=True, progress=False)["Close"].squeeze().dropna()
    return np.log(d.resample("M").last())

def slope(v): return (v[-1] - v[0]) / (len(v) - 1)

def revert(v, H):
    t = np.arange(len(v)); b, a = np.polyfit(t, v, 1); dev = v - (a + b * t)
    phi = np.clip(np.polyfit(dev[:-1], dev[1:], 1)[0], 0, 0.995)
    return a + b * (len(v) - 1 + H) + phi ** H * dev[-1]

POINT = {
    "No change": lambda v, H: v[-1],
    "Trend (current)": lambda v, H: v[-1] + slope(v) * H,
    "Trend, 5y window": lambda v, H: v[-1] + slope(v[-60:]) * H,
    "Trend, 10y window": lambda v, H: v[-1] + slope(v[-120:]) * H,
    "Trend + no change": lambda v, H: v[-1] + 0.5 * slope(v) * H,
    "Trend reversion": revert,
    "Trend + reversion": lambda v, H: 0.5 * (v[-1] + slope(v) * H) + 0.5 * revert(v, H),
}

def run(name):
    y = monthly(name); v = y.values; n = len(v); test0 = n - 72
    out = {}
    for H in (1, 3, 6, 12):
        origins = range(MIN_TRAIN, n - H)
        rec = {m: [] for m in POINT}
        for i in origins:
            tr = v[:i + 1]; a = v[i + H]; sd = np.diff(tr)[-60:].std() * np.sqrt(H)
            for m, f in POINT.items():
                p = f(tr, H)
                past = [r["e"] for r in rec[m] if r["i"] + H <= i]          # errors already known at origin i
                if len(past) >= MIN_ERRS:
                    qlo, qhi = np.quantile(past, [ALPHA / 2, 1 - ALPHA / 2]); clo, chi = p + qlo, p + qhi
                else:
                    clo, chi = p - Z80 * sd, p + Z80 * sd
                rec[m].append(dict(i=i, e=a - p, ape=abs(np.exp(p - a) - 1) * 100, a=a,
                                   g=(p - Z80 * sd, p + Z80 * sd), c=(clo, chi)))
        res = {}
        for m, rs in rec.items():
            R = pd.DataFrame(rs)
            for split, S in (("dev", R[R.i < test0 - H]), ("test", R[R.i >= test0])):
                row = {"n": len(S), "mape": S.ape.mean()}
                for band in ("g", "c"):
                    lo = np.array([b[0] for b in S[band]]); hi = np.array([b[1] for b in S[band]]); a = S.a.values
                    row[f"cov_{band}"] = ((a >= lo) & (a <= hi)).mean() * 100
                    row[f"width_{band}"] = ((np.exp(hi - lo) - 1) * 100).mean()
                    row[f"iscore_{band}"] = ((hi - lo) + 2 / ALPHA * ((lo - a) * (a < lo) + (a - hi) * (a > hi))).mean() * 100
                res[(m, split)] = row
            res[(m, "test_ape")] = R[R.i >= test0].ape.values
        out[H] = res
    return out

def report(name, out, chosen):
    print(f"\n==================== {name} ====================")
    picks = {}
    for H, res in out.items():
        rows = []
        for m in POINT:
            d, t = res[(m, "dev")], res[(m, "test")]
            rows.append([m, round(d["mape"], 2), round(t["mape"], 2), round(t["cov_g"]), round(t["cov_c"]), round(t["width_g"], 1), round(t["width_c"], 1),
                         round(d["iscore_g"], 1), round(d["iscore_c"], 1), round(t["iscore_g"], 1), round(t["iscore_c"], 1)])
        T = pd.DataFrame(rows, columns=["model", "dev_err", "TEST_err", "cov_gauss", "cov_conf", "w_gauss", "w_conf", "dev_is_g", "dev_is_c", "TEST_is_g", "TEST_is_c"])
        best, band = chosen[H]                                          # chosen on Nifty 50 DEV only
        cur = res[("Trend (current)", "test_ape")]; new = res[(best, "test_ape")]
        p = dm_pvalue(new - cur, H - 1)
        picks[H] = dict(best=best, band="conformal" if band == "c" else "gaussian", test_err=round(res[(best, "test")]["mape"], 2),
                        current_err=round(res[("Trend (current)", "test")]["mape"], 2), p_vs_current=p,
                        test_cov=round(res[(best, "test")]["cov_" + band]), test_width=round(res[(best, "test")]["width_" + band], 1),
                        current_cov=round(res[("Trend (current)", "test")]["cov_g"]), current_width=round(res[("Trend (current)", "test")]["width_g"], 1),
                        test_is=round(res[(best, "test")]["iscore_" + band], 1), current_is=round(res[("Trend (current)", "test")]["iscore_g"], 1))
        print(f"\n--- {H}-month horizon (dev n={res[('No change','dev')]['n']}, test n={res[('No change','test')]['n']}) ---")
        print(T.to_string(index=False))
        print("picked on dev:", picks[H])
    return picks

if __name__ == "__main__":
    outs = {nm: run(nm) for nm in ("Nifty 50", "Nifty Metal")}
    dev = outs["Nifty 50"]; chosen = {}
    for H, res in dev.items():
        best = min(POINT, key=lambda m: res[(m, "dev")]["mape"])
        chosen[H] = (best, "c" if res[(best, "dev")]["iscore_c"] < res[(best, "dev")]["iscore_g"] else "g")
    print("chosen on Nifty 50 dev window:", chosen)
    allp = {nm: report(nm, o, chosen) for nm, o in outs.items()}
    json.dump(allp, open("improve_results.json", "w"), indent=1, default=str)
