"""Can outside drivers (commodities, FX, global markets) improve Nifty Metal forecasts? Honest walk-forward test."""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, yfinance as yf
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

d = pd.read_csv("nifty_metal_official.csv", parse_dates=["date"]).set_index("date")["close"]
metal = np.log(d.resample("M").last())

EXT = {"copper": "HG=F", "aluminium": "ALI=F", "usdinr": "INR=X", "dxy": "DX-Y.NYB", "sp500": "^GSPC",
       "china": "000001.SS", "nifty50": "^NSEI", "crude": "CL=F", "gold": "GC=F"}
raw = yf.download(list(EXT.values()), start="2015-06-01", auto_adjust=True, progress=False)["Close"]
ext = {}
for k, t in EXT.items():
    if t in raw and raw[t].notna().sum() > 1000:
        ext[k] = np.log(raw[t].dropna().resample("M").last())
print("drivers available:", list(ext))

def build(H):
    F = pd.DataFrame(index=metal.index)
    F["m1"] = metal.diff(1); F["m3"] = metal.diff(3); F["m6"] = metal.diff(6); F["m12"] = metal.diff(12)
    F["vol12"] = metal.diff().rolling(12).std(); F["gap24"] = metal - metal.rolling(24).mean()
    for k, s in ext.items():
        s = s.reindex(metal.index).ffill()
        F[k + "_3"] = s.diff(3); F[k + "_12"] = s.diff(12)
    F["rel_n50"] = metal.diff(6) - ext["nifty50"].reindex(metal.index).ffill().diff(6) if "nifty50" in ext else 0
    F["y"] = metal.shift(-H) - metal
    return F

def evaluate(H, cols_filter):
    F = build(H); X = F.drop(columns="y"); cols = [c for c in X.columns if cols_filter(c)]
    D = F.dropna(subset=cols + ["y"]); n = len(D); start = n - 72
    P, A, B = [], [], []
    for i in range(start, n):
        tr = D.iloc[:max(i - H, 30)]                   # purge: only targets known at time i
        m = make_pipeline(StandardScaler(), Ridge(alpha=60)).fit(tr[cols], tr["y"])
        P.append(m.predict(D.iloc[[i]][cols])[0]); A.append(D["y"].iloc[i]); B.append(tr["y"].mean())
    P, A, B = map(np.array, (P, A, B))
    ens = 0.5 * P + 0.5 * B
    f = lambda p: np.mean(np.abs(np.expm1(p - A))) * 100
    return f(P), f(B), f(ens), f(np.zeros_like(A)), (np.sign(P) == np.sign(A)).mean() * 100, len(cols)

own = lambda c: c in ("m1", "m3", "m6", "m12", "vol12", "gap24")
rows = []
for H in (1, 3, 6, 12):
    for name, flt in (("own-price features", own), ("own + outside drivers", lambda c: True)):
        mp, drift, ens, zero, dr, nc = evaluate(H, flt)
        rows.append((f"{H}m", name, round(mp, 2), round(ens, 2), round(drift, 2), round(zero, 2), round(dr)))
print(pd.DataFrame(rows, columns=["horizon", "features", "ridge_err_%", "blend_err_%", "drift_err_%", "no-change_err_%", "direction_%"]).to_string(index=False))
