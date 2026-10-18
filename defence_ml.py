import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, yfinance as yf
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

N=["HAL","BEL","BDL","MAZDOCK","COCHINSHIP","BEML","SOLARINDS","DATAPATTNS","MTARTECH","ASTRAMICRO","GRSE","PARAS","MIDHANI","BHARATFORG"]
start=(pd.Timestamp.today()-pd.DateOffset(years=7)).strftime("%Y-%m-%d")
p=yf.download([n+".NS" for n in N],start=start,auto_adjust=True,progress=False)["Close"]
r=np.log(p).diff().clip(-.2,.2)
ret=r.mean(axis=1,skipna=True).dropna()          # equal-weight daily log return (stocks join as they list)
ret=ret[r.notna().sum(axis=1)>=3]
lvl=np.exp(ret.cumsum()); lvl=lvl/lvl.iloc[-1]*100
print("days",len(ret),ret.index[0].date(),"->",ret.index[-1].date())

LAGS=[1,2,3,5,10,21,63]
def feats(x):  # x: (..., T) array of past daily returns, most recent last
    f=[x[...,-l:].sum(-1) for l in LAGS]
    f+=[x[...,-21:].std(-1),x[...,-63:].std(-1),(x[...,-21:]>0).mean(-1),x[...,-1]*0+x[...,-5:].mean(-1)-x[...,-21:].mean(-1)]
    return np.stack(f,-1)
a=ret.values; W=63
X=np.stack([feats(a[:i]) for i in range(W,len(a))]); y=a[W:]; dates=ret.index[W:]
mk={"ridge":lambda:make_pipeline(StandardScaler(),Ridge(alpha=1000)),
    "gbm":lambda:HistGradientBoostingRegressor(max_depth=3,learning_rate=.03,max_iter=150,min_samples_leaf=40,l2_regularization=5)}
# walk-forward: expanding window, refit every 63 days over last ~2.5 years
t0=len(y)-630; res={m:[] for m in list(mk)+["zero","mean"]}; act=[]
for s in range(t0,len(y),63):
    e=min(s+63,len(y)); act+=list(y[s:e])
    for m in mk: res[m]+=list(mk[m]().fit(X[:s],y[:s]).predict(X[s:e]))
    res["zero"]+=[0]*(e-s); res["mean"]+=[y[:s].mean()]*(e-s)
act=np.array(act); rows=[]
for m,v in res.items():
    v=np.array(v); rows.append((m,np.sqrt(np.mean((act-v)**2))*100,(np.sign(v)==np.sign(act)).mean()*100 if m not in("zero",) else np.nan,np.corrcoef(v,act)[0,1] if v.std()>0 else np.nan))
bt=pd.DataFrame(rows,columns=["model","RMSE_%","hit_rate_%","corr"]).round(3); print(bt.to_string(index=False))
best=min(mk,key=lambda m:bt.set_index("model").loc[m,"RMSE_%"])
print("best ML model:",best)
model=mk[best]().fit(X,y); resid=y-model.predict(X)
# recursive Monte-Carlo to 31-Dec-2027
days=pd.bdate_range(ret.index[-1]+pd.Timedelta(days=1),"2027-12-31"); H=len(days); P=2000
rng=np.random.default_rng(0); buf=np.tile(a[-W:],(P,1)); out=np.zeros((P,H))
for t in range(H):
    mu=model.predict(feats(buf)); step=mu+rng.choice(resid,P)
    out[:,t]=step; buf=np.concatenate([buf[:,1:],step[:,None]],1)
paths=lvl.iloc[-1]*np.exp(out.cumsum(1)); q=np.percentile(paths,[10,50,90],axis=0)
print(f"Dec-2027: median {q[1,-1]:.1f} (p10 {q[0,-1]:.1f}, p90 {q[2,-1]:.1f}) from {lvl.iloc[-1]:.0f}; {H} trading days")
for d in ["2026-12-31","2027-06-30"]:
    i=days.get_indexer([pd.Timestamp(d)],method="pad")[0]; print(d,round(q[1,i],1),round(q[0,i],1),round(q[2,i],1))
pd.DataFrame({"date":days,"p10":q[0],"median":q[1],"p90":q[2]}).to_csv("defence_ml_forecast.csv",index=False)
plt.figure(figsize=(10,5));plt.plot(lvl,c="k",label="Defence proxy (rebased 100)");plt.plot(days,q[1],c="C0",label="ML median")
plt.fill_between(days,q[0],q[2],alpha=.2);plt.legend();plt.title("Nifty Defence proxy – ML forecast");plt.savefig("defence_ml.png",dpi=110)

import json
m=lvl.resample("M").last(); f=pd.DataFrame({"p10":q[0],"med":q[1],"p90":q[2]},index=days).resample("M").last()
d=json.load(open("data.json"))
d["Nifty Defence (ML)"]={"Index":"Nifty Defence (ML)","Data":"constituent proxy, rebased to 100","Current":100,"Best_model":best+" (ML, recursive MC)",
 "Dec2027_forecast":round(float(q[1,-1]),1),"Low_p10":round(float(q[0,-1]),1),"High_p90":round(float(q[2,-1]),1),"Change_pct":round(float(q[1,-1]-100),1),
 "MAE_best_pct":None,"MAE_naive_pct":None,
 "hist":[[i.strftime("%Y-%m"),round(float(v),1)] for i,v in m.items()],
 "fc":[[i.strftime("%Y-%m"),round(float(r.med),1),round(float(r.p10),1),round(float(r.p90),1)] for i,r in f.iterrows()],"check":None}
json.dump(d,open("data.json","w"))
