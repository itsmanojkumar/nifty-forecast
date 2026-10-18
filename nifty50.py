"""Nifty 50: walk-forward model selection, forecast to Dec 2027, 15-day forecast, dashboard (nifty50.html)."""
import warnings; warnings.filterwarnings("ignore")
import json, numpy as np, pandas as pd, yfinance as yf
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA

d = yf.download("^NSEI", start="2007-09-01", auto_adjust=True, progress=False)["Close"].squeeze().dropna()
asof = d.index[-1]
print("daily rows", len(d), d.index[0].date(), "->", asof.date(), "last", round(float(d.iloc[-1])))
y = np.log(d.resample("M").last())
if d.index[-1].month == y.index[-1].month and d.index[-1] < y.index[-1]:
    pass  # last month is partial; kept (its value is the latest close)

def fc(tr, H, m):
    if m == "No change": return np.repeat(tr.iloc[-1], H)
    if m == "Trend": return tr.iloc[-1] + (tr.iloc[-1] - tr.iloc[0]) / (len(tr) - 1) * np.arange(1, H + 1)
    if m == "Smoothing": return ExponentialSmoothing(tr.values, trend="add", damped_trend=True).fit().forecast(H)
    if m == "ARIMA": return ARIMA(tr.values, order=(1, 1, 1), trend="t").fit().forecast(H)
M = ["No change", "Trend", "Smoothing", "ARIMA"]
res = {}
for H in (1, 3, 6, 12):
    rows = []
    for i in range(len(y) - 72, len(y) - H):
        tr = y.iloc[:i + 1]; a = y.iloc[i + H]; b = tr.iloc[-1]
        for m in M:
            p = fc(tr, H, m)[-1]
            rows.append((m, abs(np.exp(p - a) - 1) * 100, np.sign(p - b) == np.sign(a - b)))
    t = pd.DataFrame(rows, columns=["m", "err", "dir"]).groupby("m").agg(err=("err", "mean"), dir=("dir", "mean"))
    res[H] = t
    print(H, "m\n", t.round(3).to_string())
best = res[12]["err"].drop("No change").idxmin(); print("best 12m model:", best)
acc = [{"h": f"{h} month{'s' if h > 1 else ''}", "err": round(float(res[h].loc[best, "err"]), 1), "dir": round(float(res[h].loc[best, "dir"] * 100))} for h in (1, 3, 6, 12)]
models = sorted([[m + (" (winner)" if m == best else ""), round(float(res[12].loc[m, "err"]), 1)] for m in M], key=lambda x: x[1])

H = (2027 - y.index[-1].year) * 12 + 12 - y.index[-1].month
path = fc(y, H, best); sd = y.diff().dropna().values[-60:].std()
kk = np.sqrt(np.arange(1, H + 1)) * sd * 1.2816
fd = pd.date_range(y.index[-1], periods=H + 1, freq="M")[1:]
cur = float(d.iloc[-1])
fcm = [[i.strftime("%Y-%m"), round(float(np.exp(a)), 1), round(float(np.exp(a - b)), 1), round(float(np.exp(a + b)), 1)] for i, a, b in zip(fd, path, kk)]
# 12-month holdout check
tr, te = y.iloc[:-12], y.iloc[-12:]; p = fc(tr, 12, best); k2 = np.sqrt(np.arange(1, 13)) * tr.diff().dropna().values[-60:].std() * 1.2816
check = {"mape_pct": round(float(np.mean(np.abs(np.exp(p) / np.exp(te.values) - 1)) * 100), 1), "end_err_pct": round(float((np.exp(p[-1]) / np.exp(te.values[-1]) - 1) * 100), 1),
         "inside_band_pct": round(float(((te.values >= p - k2) & (te.values <= p + k2)).mean() * 100)), "pred": [round(float(np.exp(v))) for v in p],
         "actual": [round(float(np.exp(v))) for v in te.values], "months": [i.strftime("%Y-%m") for i in te.index]}
# next 15 trading days
r = np.log(d).diff().dropna(); mu = r.iloc[-1260:].mean(); s21 = r.iloc[-21:].std(); days = pd.bdate_range(asof + pd.Timedelta(days=1), periods=15)
short = {"hist": [[i.strftime("%d %b"), round(float(v), 1)] for i, v in d.tail(30).items()],
         "fc": [[x.strftime("%d %b"), round(cur * float(np.exp(mu * n)), 1), round(cur * float(np.exp(mu * n - 1.2816 * s21 * np.sqrt(n))), 1), round(cur * float(np.exp(mu * n + 1.2816 * s21 * np.sqrt(n))), 1)] for x, n in zip(days, range(1, 16))]}
m = d.resample("M").last()
out = {"asof": asof.strftime("%d %b %Y"), "current": round(cur), "hist": [[i.strftime("%Y-%m"), round(float(v), 1)] for i, v in m.items()],
       "fc": fcm, "check": check, "acc": acc, "models": models, "short": short}
t = open("template_metal.html", encoding="utf-8").read()
for a, b in [("Nifty Metal Forecast", "Nifty 50 Forecast"), ("Official NSE index data · Nov 2015 – Oct 2026", f"Index data from Yahoo Finance · Sep 2007 – {asof.strftime('%b %Y')}"),
             ("Where the Nifty Metal index", "Where the Nifty 50 index"), ("Trend (winner)", "Trend (winner)")]:
    t = t.replace(a, b)
t = t.replace("Past prices alone could not predict next month's move: Ridge and gradient boosting models scored about the same as guessing on direction. ", "Past prices alone gave little edge over assuming no change beyond the long-run trend. ")
t = t.replace("The simple trend won; ML models did worse.", f"The {best.lower()} model won; the differences are small.")
t = t.replace("<p style=\"margin:0\">I also tested adding copper, aluminium, crude, gold, USD/INR, the dollar index, S&amp;P 500, China and Nifty 50. None of them improved the forecast in a walk-forward test, so they are not used.</p>", "")
t = t.replace("roughly ±17%", f"roughly ±{acc[3]['err']:.0f}%").replace("startsWith(\"Trend\")", "includes(\"winner\")")
open("nifty50.html", "w", encoding="utf-8").write(t.replace("__DATA__", json.dumps(out)))
json.dump(out, open("data_nifty50.json", "w"))
f = fcm[-1]; print(f"NOW {cur:.0f}  DEC2027 {f[1]:.0f} ({(f[1]/cur-1)*100:+.1f}%)  80% {f[2]:.0f}-{f[3]:.0f}  | tmrw {short['fc'][0][1:]}  | 15d {short['fc'][-1]}")
print("acc", acc); print("check", {k: v for k, v in check.items() if k in ("mape_pct", "end_err_pct", "inside_band_pct")})
