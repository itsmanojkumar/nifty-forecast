"""Nifty 50 short-term forecasts (1, 5, 15 trading days): do outside data improve them? Honest walk-forward test.

Forecast time: 08:45 IST on trading day t, before NSE opens. Only information known then is used:
  global   - US (S&P 500, Nasdaq, S&P futures) closes of sessions that ended overnight; Asia only up to yesterday
  vol      - India VIX and Nifty high/low ranges up to yesterday's close
  calendar - expiry day, pre/post holiday, Budget day, results season, weekday
  options  - NIFTY options/futures end-of-day aggregates from yesterday (data/nifty_options_daily.csv)
Target: log return from yesterday's close (t-1) to the close of t+h-1, h in {1, 5, 15}.
Selection window (DEV) 2019-2021, report window (TEST) 2022 onward; models refit every 63 trading days, purged.
"""
import warnings; warnings.filterwarnings("ignore")
import json, os, sys, numpy as np, pandas as pd, yfinance as yf
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DEV0, TEST0, TRAIN0 = "2019-01-01", "2022-01-01", "2016-01-01"
STEP, Z80, ALPHA = 63, 1.2816, 0.2
BUDGET = ["2016-02-29", "2017-02-01", "2018-02-01", "2019-02-01", "2019-07-05", "2020-02-01", "2021-02-01", "2022-02-01",
          "2023-02-01", "2024-02-01", "2024-07-23", "2025-02-01", "2026-02-01"]

def dm_pvalue(d, lag):
    d = np.asarray(d, float); n = len(d); u = d - d.mean()
    if np.allclose(u, 0): return None
    v = u @ u / n
    for k in range(1, lag + 1): v += 2 * (1 - k / (lag + 1)) * (u[k:] @ u[:-k]) / n
    return round(float(2 * stats.t.sf(abs(d.mean() / np.sqrt(v / n)), n - 1)), 4)

# ---------------------------------------------------------------- data
def load():
    tick = {"nifty": "^NSEI", "vix": "^INDIAVIX", "spx": "^GSPC", "ndx": "^IXIC", "es": "ES=F", "nikkei": "^N225", "hsi": "^HSI", "shanghai": "000001.SS"}
    raw = yf.download(list(tick.values()), start="2014-01-01", auto_adjust=True, progress=False, group_by="ticker")
    get = lambda t, f="Close": raw[t][f].dropna()
    n = raw["^NSEI"][["Open", "High", "Low", "Close"]].dropna()
    n = n[(n.High > 0) & (n.Low > 0)]
    other = {k: get(t) for k, t in tick.items() if k != "nifty"}
    return n, other

def before(series, dates, max_age_days=None):
    """last value of `series` dated strictly before each date in `dates` (known at 08:45 IST on that date).
    With max_age_days, values older than that count as missing instead of being carried forward."""
    s = series.dropna().sort_index(); pos = s.index.searchsorted(dates, side="left") - 1
    ok = pos >= 0; p = np.clip(pos, 0, None)
    if max_age_days is not None:
        ok &= (pd.DatetimeIndex(dates) - s.index[p]).days <= max_age_days
    return pd.Series(np.where(ok, s.values[p], np.nan), index=dates)

def build(n, other, opts):
    idx = n.index; c = np.log(n.Close); r = c.diff()
    prev = pd.Series(idx, index=idx).shift(1)                   # previous NSE trading day
    F = pd.DataFrame(index=idx)
    # own price (all lagged: known at yesterday's close)
    F["r1"] = r.shift(1); F["r5"] = c.diff(5).shift(1); F["r21"] = c.diff(21).shift(1); F["ma50_gap"] = (c - c.rolling(50).mean()).shift(1)
    own = list(F.columns)
    # global overnight: US sessions with date in [prev, t) ; Asia: sessions with date < t (closed before India's prev close)
    for k in ("spx", "ndx", "es"):
        lc = np.log(other[k]); F[f"us_{k}"] = before(lc, idx).values - before(lc, prev.fillna(idx[0])).values
    for k in ("nikkei", "hsi", "shanghai"):
        lc = np.log(other[k]); b = before(lc, idx); F[f"asia_{k}"] = b - b.shift(1)
    glob = [x for x in F.columns if x.startswith(("us_", "asia_"))]
    # volatility
    pk = np.sqrt((np.log(n.High / n.Low) ** 2) / (4 * np.log(2)))  # Parkinson daily vol
    lv = np.log(other["vix"]); vb = before(lv, idx)                             # India VIX close of yesterday
    F["vix"] = vb; F["vix_chg"] = vb - vb.shift(1); F["rv5"] = np.log(pk.rolling(5).mean().shift(1)); F["rv21"] = np.log(pk.rolling(21).mean().shift(1))
    F["absr1"] = r.abs().shift(1)
    vol = ["vix", "vix_chg", "rv5", "rv21", "absr1"]
    # calendar
    dts = pd.Series(idx, index=idx); nxt = dts.shift(-1); gap_next = (nxt - dts).dt.days; gap_prev = (dts - prev).dt.days
    wd = idx.weekday
    F["pre_holiday"] = ((gap_next > 1) & ~((wd == 4) & (gap_next == 3))).astype(float)
    F["post_holiday"] = ((gap_prev > 1) & ~((wd == 0) & (gap_prev == 3))).astype(float)
    exp_wd = np.where(idx >= pd.Timestamp("2025-09-01"), 1, 3)   # Tuesday from Sep 2025, Thursday before
    week = idx.to_period("W")
    exp = np.zeros(len(idx))
    for w, grp in pd.Series(np.arange(len(idx)), index=idx).groupby(week):
        days = grp.index; target = exp_wd[grp.values[0]]
        cand = [i for d, i in zip(days, grp.values) if d.weekday() <= target]
        if cand: exp[cand[-1]] = 1
    weekly_from = pd.Timestamp("2019-02-11")
    month = idx.to_period("M"); mexp = np.zeros(len(idx))
    ex = pd.Series(exp, index=idx)
    for m, grp in ex.groupby(month):
        e = grp[grp == 1]
        if len(e): mexp[idx.get_loc(e.index[-1])] = 1
    F["weekly_expiry"] = np.where(idx >= weekly_from, exp, 0.0); F["monthly_expiry"] = mexp
    F["budget"] = idx.isin(pd.to_datetime(BUDGET)).astype(float)
    md = idx.month * 100 + idx.day
    F["results_season"] = (((md >= 110) & (md <= 215)) | ((md >= 410) & (md <= 520)) | ((md >= 710) & (md <= 815)) | ((md >= 1010) & (md <= 1115))).astype(float)
    for k in range(5): F[f"dow{k}"] = (wd == k).astype(float)
    cal = ["pre_holiday", "post_holiday", "weekly_expiry", "monthly_expiry", "budget", "results_season"] + [f"dow{k}" for k in range(5)]
    # options (yesterday's EOD)
    o = opts.set_index(pd.to_datetime(opts.date)).sort_index()
    o["basis"] = np.log(o.fut_close) - np.log(n.Close.reindex(o.index))
    o["oi_skew"] = (o.put_oi_chg - o.call_oi_chg) / (o.put_oi + o.call_oi)
    o["fut_oi_chg_pct"] = o.fut_oi_chg / o.fut_oi
    ocols = ["pcr_oi", "pcr_vol", "near_pcr_oi", "oi_skew", "basis", "fut_oi_chg_pct"]
    for k in ocols: F["opt_" + k] = before(o[k], idx, 7).values
    F["opt_pcr_oi_chg"] = F.opt_pcr_oi - before(o.pcr_oi, prev.fillna(idx[0]), 7).values
    opt = ["opt_" + k for k in ocols] + ["opt_pcr_oi_chg"]
    # targets: close(t+h-1) / close(t-1)
    Y = {h: c.shift(-(h - 1)) - c.shift(1) for h in (1, 5, 15)}
    return F, Y, r, {"own": own, "global": glob, "vol": vol, "calendar": cal, "options": opt}

# ---------------------------------------------------------------- evaluation
def walk(F, y, cols, h, kind):
    D = pd.concat([F[cols], y.rename("y")], axis=1).loc[TRAIN0:].dropna()
    X, Yv, ix = D[cols].values, D.y.values, D.index
    start = ix.searchsorted(pd.Timestamp(DEV0)); pred = np.full(len(D), np.nan)
    for s in range(start, len(D), STEP):
        e = min(s + STEP, len(D)); tr = slice(0, max(s - h, 50))
        m = make_pipeline(StandardScaler(), Ridge(alpha=200)) if kind == "ridge" else \
            HistGradientBoostingRegressor(max_depth=3, learning_rate=0.03, max_iter=200, min_samples_leaf=80, l2_regularization=10, random_state=0)
        pred[s:e] = m.fit(X[tr], Yv[tr]).predict(X[s:e])
    return pd.Series(pred, index=ix)

def point_metrics(p, a, h):
    e, z = p - a, -a
    return dict(n=len(a), rmse=round(float(np.sqrt(np.mean(e ** 2)) * 100), 3), mae=round(float(np.mean(np.abs(e)) * 100), 3),
                r2_vs_zero=round(float((1 - np.sum(e ** 2) / np.sum(z ** 2)) * 100), 2),
                direction=round(float((np.sign(p) == np.sign(a)).mean() * 100), 1), up_share=round(float((a > 0).mean() * 100), 1),
                corr=round(float(np.corrcoef(p, a)[0, 1]), 3) if np.std(p) > 0 else None, p_vs_zero=dm_pvalue(e ** 2 - z ** 2, h - 1))

def sigma_models(F, r, h):
    """per-day forecast of the h-day return's std, using only info before the open."""
    rr = r.shift(1)
    s21 = rr.rolling(21).std() * np.sqrt(h)                                    # current production rule
    ew = np.sqrt((rr ** 2).ewm(alpha=0.06).mean()) * np.sqrt(h)                # EWMA (RiskMetrics)
    vx = np.exp(F.vix) / 100 / np.sqrt(252) * np.sqrt(h)                       # India VIX implied
    return {"21-day stdev (current)": s21, "EWMA": ew, "India VIX": vx}

def har_sigma(F, y, h, cols):
    """regression of log|h-day return| on vol + calendar features, refit walk-forward (HAR-style)."""
    D = pd.concat([F[cols], np.log(y.abs() + 1e-4).rename("t")], axis=1).loc[TRAIN0:].dropna()
    X, T, ix = D[cols].values, D.t.values, D.index; out = np.full(len(D), np.nan)
    start = ix.searchsorted(pd.Timestamp(DEV0))
    for s in range(start, len(D), STEP):
        e = min(s + STEP, len(D)); tr = slice(0, max(s - h, 50))
        m = make_pipeline(StandardScaler(), Ridge(alpha=50)).fit(X[tr], T[tr]); out[s:e] = np.exp(m.predict(X[s:e]))
    return pd.Series(out, index=ix)

def band_metrics(point, sig, a, h, label):
    """band = point + q * sigma with q the 10/90% quantiles of past standardized errors (known at the time)."""
    df = pd.concat([point.rename("p"), sig.rename("s"), a.rename("a")], axis=1).dropna()
    z = (df.a - df.p) / df.s; lo, hi = [], []
    for i in range(len(df)):
        past = z.iloc[:max(i - h + 1, 0)]
        if len(past) >= 250: ql, qh = np.quantile(past.iloc[-1000:], [ALPHA / 2, 1 - ALPHA / 2])
        else: ql, qh = -Z80, Z80
        lo.append(df.p.iloc[i] + ql * df.s.iloc[i]); hi.append(df.p.iloc[i] + qh * df.s.iloc[i])
    df["lo"], df["hi"] = lo, hi
    res = {}
    for split, S in (("dev", df.loc[DEV0:TEST0]), ("test", df.loc[TEST0:])):
        a_, l_, h_ = S.a.values, S.lo.values, S.hi.values
        res[split] = dict(coverage=round(float(((a_ >= l_) & (a_ <= h_)).mean() * 100), 1), width=round(float(((np.exp(h_ - l_) - 1) * 100).mean()), 2),
                          iscore=round(float(((h_ - l_) + 2 / ALPHA * ((l_ - a_) * (a_ < l_) + (a_ - h_) * (a_ > h_))).mean() * 100), 3))
    return res

def main(use_options=True):
    n, other = load()
    opts = pd.read_csv("data/nifty_options_daily.csv")
    F, Y, r, G = build(n, other, opts)
    print("rows", len(F), F.index[0].date(), "->", F.index[-1].date(), "| options from", opts.date.min())
    sets = {"own price only": G["own"], "+ global overnight": G["own"] + G["global"], "+ volatility": G["own"] + G["vol"],
            "+ calendar": G["own"] + G["calendar"], "+ options": G["own"] + G["options"], "all four": sum(G.values(), [])}
    if not use_options:
        sets.pop("+ options"); sets["all three"] = G["own"] + G["global"] + G["vol"] + G["calendar"]; sets.pop("all four")
    out = {"features": G, "point": {}, "range": {}}
    for h in (1, 5, 15):
        y = Y[h]; rows = []
        for name, cols in sets.items():
            for kind in ("ridge", "boosting"):
                p = walk(F, y, cols, h, kind)
                for split, a0, a1 in (("dev", DEV0, TEST0), ("test", TEST0, None)):
                    P = p.loc[a0:a1].dropna(); A = y.reindex(P.index); ok = A.notna(); P, A = P[ok], A[ok]
                    rows.append(dict(h=h, features=name, model=kind, split=split, **point_metrics(P.values, A.values, h)))
        T = pd.DataFrame(rows); out["point"][h] = rows
        print(f"\n=========== {h}-day ahead: point forecast (R2 vs 'no change', %; >0 = better) ===========")
        print(T.pivot_table(index=["features", "model"], columns="split", values=["r2_vs_zero", "direction", "p_vs_zero"]).round(3).to_string())
        # ranges around a zero/drift point (direction is a coin flip, so the band carries the information)
        zero = pd.Series(0.0, index=y.index)
        sig = sigma_models(F, r, h); sig["HAR (vol + calendar)"] = har_sigma(F, y, h, G["vol"] + G["calendar"])
        if use_options: sig["HAR (vol + calendar + options)"] = har_sigma(F, y, h, G["vol"] + G["calendar"] + G["options"])
        brows = {k: band_metrics(zero, s, y, h, k) for k, s in sig.items()}
        out["range"][h] = brows
        print(f"--- {h}-day 80% range (coverage target 80; lower interval score = better) ---")
        print(pd.DataFrame({k: {f"{sp}_{m}": v[sp][m] for sp in v for m in v[sp]} for k, v in brows.items()}).T.to_string())
    json.dump(out, open("short_term_results.json" if use_options else "short_term_results_no_options.json", "w"), indent=1, default=float)

if __name__ == "__main__":
    main(use_options="--no-options" not in sys.argv)
