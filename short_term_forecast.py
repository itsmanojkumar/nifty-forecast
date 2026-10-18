"""Production 15-day forecast for Nifty 50 (replaces the drift-only 'short' block in data_nifty50.json).

Chosen in short_term_eval.py (DEV 2019-21, confirmed on TEST 2022+):
  - day 1: gradient boosting on own price features + overnight global moves (US closes that ended before 08:45 IST)
  - days 2-15: day-1 forecast plus the 5-year average daily drift
  - 80% range: India VIX scaled to k days, bounds = 10/90% quantiles of past standardized errors (last 1000 days)
Run after the US close / before 08:45 IST for the next NSE session, then build_all.py to refresh the site.
"""
import warnings; warnings.filterwarnings("ignore")
import json, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
import short_term_eval as st

H_MAX, CAL = 15, 1000

def model():
    return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.03, max_iter=200, min_samples_leaf=80, l2_regularization=10, random_state=0)

def main():
    n, other = st.load(); opts = pd.read_csv("data/nifty_options_daily.csv")
    last = n.index[-1]; nxt = pd.bdate_range(last + pd.Timedelta(days=1), periods=H_MAX)
    ext = pd.concat([n, pd.DataFrame(index=nxt[:1], columns=n.columns, dtype=float)])   # empty row for the next session
    F, Y, r, G = st.build(ext, other, opts)
    cols = G["own"] + G["global"]; y1 = Y[1]

    # walk-forward day-1 predictions (for calibrating the range on the model's own past errors)
    hist = st.walk(F.iloc[:-1], y1.iloc[:-1], cols, 1, "boosting")
    # final fit on everything known, predict the next session
    D = pd.concat([F[cols], y1.rename("y")], axis=1).loc[st.TRAIN0:].iloc[:-1].dropna()
    p1 = float(model().fit(D[cols].values, D.y.values).predict(F[cols].iloc[[-1]].values)[0])

    c = np.log(n.Close); rr = c.diff().dropna(); mu = float(rr.iloc[-1260:].mean())
    vix = float(np.exp(F.vix.iloc[-1])); cur = float(n.Close.iloc[-1])
    fc, calib = [], {}
    for k in range(1, H_MAX + 1):
        yk = (c.shift(-(k - 1)) - c.shift(1))                       # realised k-day return from the prior close
        sig_hist = np.exp(F.vix.iloc[:-1]) / 100 / np.sqrt(252) * np.sqrt(k)
        pt_hist = hist + mu * (k - 1)
        z = ((yk.iloc[:-1] - pt_hist) / sig_hist).dropna().iloc[-CAL:]
        ql, qh = np.quantile(z, [0.1, 0.9]); calib[k] = (round(float(ql), 3), round(float(qh), 3), len(z))
        pt = p1 + mu * (k - 1); s = vix / 100 / np.sqrt(252) * np.sqrt(k)
        fc.append([nxt[k - 1].strftime("%d %b"), round(cur * np.exp(pt), 1), round(cur * np.exp(pt + ql * s), 1), round(cur * np.exp(pt + qh * s), 1)])

    us = {k.replace("us_", ""): round(float(F[k].iloc[-1]) * 100, 2) for k in ("us_spx", "us_ndx", "us_es")}
    meta = {"made_for": nxt[0].strftime("%d %b %Y"), "last_close_date": last.strftime("%d %b %Y"), "last_close": round(cur, 1),
            "day1_return_pct": round(p1 * 100, 3), "drift_pct_per_day": round(mu * 100, 4), "india_vix": round(vix, 2),
            "overnight_pct": us, "model": "Gradient boosting on own price + overnight global moves (day 1); drift after; India VIX range",
            "calibration_quantiles": {str(k): v for k, v in calib.items() if k in (1, 5, 15)}}
    d = json.load(open("data_nifty50.json"))
    d["short"]["fc"] = fc; d["short"]["hist"] = [[i.strftime("%d %b"), round(float(v), 1)] for i, v in n.Close.tail(30).items()]
    d["short_meta"] = meta
    json.dump(d, open("data_nifty50.json", "w"))
    print(json.dumps(meta, indent=1)); print("day 1:", fc[0], "| day 15:", fc[-1])

if __name__ == "__main__":
    main()
