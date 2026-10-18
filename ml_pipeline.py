"""Full ML pipeline: tuned classical models + GRU neural net + ensemble, purged walk-forward evaluation, significance test.

Target: log return over the next H=21 trading days, for Nifty Metal and Nifty 50 (daily data).
"""
import warnings; warnings.filterwarnings("ignore")
import json, numpy as np, pandas as pd, torch, torch.nn as nn, yfinance as yf
from scipy import stats
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

H, SEQ, SEED = 21, 60, 0
torch.manual_seed(SEED); np.random.seed(SEED)

def load(name):
    if name == "Nifty Metal":
        return pd.read_csv("nifty_metal_official.csv", parse_dates=["date"]).set_index("date")["close"]
    return yf.download("^NSEI", start="2007-09-01", auto_adjust=True, progress=False)["Close"].squeeze().dropna()

def features(close):
    ly = np.log(close); r = ly.diff()
    F = pd.DataFrame({f"r{k}": ly.diff(k) for k in (1, 5, 10, 21, 63, 126, 252)})
    F["vol21"] = r.rolling(21).std(); F["vol63"] = r.rolling(63).std()
    F["dd"] = ly - ly.rolling(252).max(); F["ma_gap"] = ly - ly.rolling(100).mean()
    F["y"] = ly.shift(-H) - ly
    return F, r

class GRUNet(nn.Module):
    def __init__(self, n_in, hidden=16):
        super().__init__(); self.gru = nn.GRU(n_in, hidden, batch_first=True); self.head = nn.Sequential(nn.Dropout(0.2), nn.Linear(hidden, 1))
    def forward(self, x): return self.head(self.gru(x)[0][:, -1]).squeeze(-1)

def fit_gru(Xs, y, epochs=25):
    m = GRUNet(Xs.shape[-1]); opt = torch.optim.AdamW(m.parameters(), lr=3e-3, weight_decay=1e-3)
    X = torch.tensor(Xs, dtype=torch.float32); t = torch.tensor(y / y.std(), dtype=torch.float32)
    n_val = max(int(len(X) * 0.15), 20); Xt, tt, Xv, tv = X[:-n_val], t[:-n_val], X[-n_val:], t[-n_val:]
    best, best_state, bad = 1e9, None, 0
    for _ in range(epochs):                      # early stopping on the last 15% of training data
        m.train(); perm = torch.randperm(len(Xt))
        for i in range(0, len(Xt), 64):
            b = perm[i:i + 64]; opt.zero_grad(); nn.functional.mse_loss(m(Xt[b]), tt[b]).backward(); opt.step()
        m.eval()
        with torch.no_grad(): v = nn.functional.mse_loss(m(Xv), tv).item()
        if v < best - 1e-4: best, best_state, bad = v, {k: x.clone() for k, x in m.state_dict().items()}, 0
        else:
            bad += 1
            if bad >= 4: break
    m.load_state_dict(best_state); return m, y.std()

def run(name):
    close = load(name); F, r = features(close); D = F.dropna(); idx = D.index
    X, y = D.drop(columns="y").values, D["y"].values
    rv = r.reindex(idx).values; rr = r.values; pos = {d: i for i, d in enumerate(r.index)}
    seqs = np.stack([rr[pos[d] - SEQ + 1: pos[d] + 1] for d in idx])[..., None] / (np.nanstd(rr) + 1e-9)   # daily return sequences
    n = len(D); start = n - 1260; step = 126
    P = {k: [] for k in ["No change", "Trend", "Ridge", "Random forest", "Boosting (tuned)", "GRU neural net", "Ensemble"]}; A = []
    chosen = []
    for s in range(start, n, step):
        e = min(s + step, n); tr = slice(0, s - H)             # purge: training targets must be known at time s
        A += list(y[s:e]); mu = y[tr].mean()
        P["No change"] += [0.0] * (e - s); P["Trend"] += [mu] * (e - s)
        P["Ridge"] += list(make_pipeline(StandardScaler(), Ridge(alpha=3000)).fit(X[tr], y[tr]).predict(X[s:e]))
        P["Random forest"] += list(RandomForestRegressor(200, max_depth=4, min_samples_leaf=60, n_jobs=-1, random_state=SEED).fit(X[tr], y[tr]).predict(X[s:e]))
        gs = GridSearchCV(HistGradientBoostingRegressor(max_iter=120, min_samples_leaf=60, l2_regularization=10, random_state=SEED),
                          {"max_depth": [2, 3], "learning_rate": [0.02, 0.05]}, cv=TimeSeriesSplit(4), scoring="neg_mean_squared_error").fit(X[tr], y[tr])
        chosen.append(gs.best_params_); P["Boosting (tuned)"] += list(gs.predict(X[s:e]))
        net, sd = fit_gru(seqs[tr], y[tr]); net.eval()
        with torch.no_grad(): P["GRU neural net"] += list(net(torch.tensor(seqs[s:e], dtype=torch.float32)).numpy() * sd)
    A = np.array(A); P = {k: np.array(v) for k, v in P.items()}
    P["Ensemble"] = (P["Trend"] + P["Ridge"] + P["Boosting (tuned)"] + P["GRU neural net"]) / 4
    base = (P["Trend"] - A) ** 2; rows = []
    for k, v in P.items():
        d = (v - A) ** 2 - base                                  # loss differential vs Trend baseline
        t_, p_ = (np.nan, np.nan) if np.allclose(d, 0) else stats.ttest_1samp(d, 0)   # simplified Diebold-Mariano (overlapping targets: indicative only)
        rows.append({"model": k, "MAPE_%": round(float(np.mean(np.abs(np.expm1(v - A))) * 100), 2), "RMSE_%": round(float(np.sqrt(np.mean((v - A) ** 2)) * 100), 2),
                     "direction_%": round(float((np.sign(v) == np.sign(A)).mean() * 100)) if k != "No change" else None,
                     "corr": round(float(np.corrcoef(v, A)[0, 1]), 3) if v.std() > 0 else None, "p_vs_trend": None if np.isnan(p_) else round(float(p_), 3)})
    T = pd.DataFrame(rows); print(f"\n=== {name}: {len(D)} daily rows, test {len(A)} days, horizon {H} trading days ==="); print(T.to_string(index=False))
    print("tuned boosting params per refit:", chosen)
    test_dates = [d.strftime("%Y-%m-%d") for d in idx[start:n]]
    return {"name": name, "rows": len(D), "test_days": int(len(A)), "table": rows, "dates": test_dates, "actual": A, "pred": P}

if __name__ == "__main__":
    out = [run(n) for n in ("Nifty Metal", "Nifty 50")]
    json.dump([{k: v for k, v in o.items() if k in ("name", "rows", "test_days", "table")} for o in out], open("ml_results.json", "w"), indent=1)
