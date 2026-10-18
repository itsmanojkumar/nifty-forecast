"""Round 2 for the Nifty 50 1-day forecast: more overnight signals and model variants.

Same protocol as short_term_eval.py: pick on DEV (2019-2021), report on TEST (2022+), refit every 63 days.
New overnight signals (sessions that ended before 08:45 IST): US VIX, US 10y yield, crude oil, dollar index.
"""
import warnings; warnings.filterwarnings("ignore")
import json, numpy as np, pandas as pd, yfinance as yf
import short_term_eval as st

EXTRA = {"us_vix": "^VIX", "us_10y": "^TNX", "crude": "CL=F", "dxy": "DX-Y.NYB"}

def add_extra(F):
    raw = yf.download(list(EXTRA.values()), start="2014-01-01", auto_adjust=True, progress=False)["Close"]
    idx = F.index; prev = pd.Series(idx, index=idx).shift(1).fillna(idx[0])
    for k, t in EXTRA.items():
        s = raw[t].dropna()
        s = s if k == "us_10y" else np.log(s)                       # yield: change in points; others: log change
        F[k] = st.before(s, idx).values - st.before(s, prev).values
    return list(EXTRA)

def blend(F, y, cols, h=1):
    return 0.5 * st.walk(F, y, cols, h, "ridge") + 0.5 * st.walk(F, y, cols, h, "boosting")

def main():
    n, other = st.load(); opts = pd.read_csv("data/nifty_options_daily.csv")
    F, Y, r, G = st.build(n, other, opts); extra = add_extra(F); y = Y[1]
    base = G["own"] + G["global"]; us_only = G["own"] + ["us_spx", "us_ndx", "us_es"]
    sets = {"own + global (current winner)": base, "own + US only": us_only,
            "own + global + extra overnight": base + extra, "own + US + extra overnight": us_only + extra}
    rows = []
    for name, cols in sets.items():
        preds = {"ridge": st.walk(F, y, cols, 1, "ridge"), "boosting": st.walk(F, y, cols, 1, "boosting")}
        preds["ridge + boosting"] = 0.5 * preds["ridge"] + 0.5 * preds["boosting"]
        for kind, p in preds.items():
            for split, a0, a1 in (("dev", st.DEV0, st.TEST0), ("test", st.TEST0, None)):
                P = p.loc[a0:a1].dropna(); A = y.reindex(P.index); ok = A.notna()
                rows.append(dict(features=name, model=kind, split=split, **st.point_metrics(P[ok].values, A[ok].values, 1)))
    T = pd.DataFrame(rows)
    print(T.pivot_table(index=["features", "model"], columns="split", values=["r2_vs_zero", "direction", "p_vs_zero"]).round(3).to_string())
    dev = T[T.split == "dev"].sort_values("r2_vs_zero", ascending=False).iloc[0]
    test = T[(T.split == "test") & (T.features == dev.features) & (T.model == dev.model)].iloc[0]
    print("\nchosen on DEV:", dev.features, "/", dev.model, f"| dev R2 {dev.r2_vs_zero}% -> TEST R2 {test.r2_vs_zero}%, direction {test.direction}%, p {test.p_vs_zero}")
    json.dump({"rows": rows, "chosen": {"features": dev.features, "model": dev.model}}, open("short_term_v2_results.json", "w"), indent=1, default=float)

if __name__ == "__main__":
    main()
