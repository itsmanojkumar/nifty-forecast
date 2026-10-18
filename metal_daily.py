import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, json
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
d=pd.read_csv("nifty_metal_official.csv",parse_dates=["date"]).set_index("date")["close"]; ly=np.log(d); r=ly.diff()
F=pd.DataFrame({f"r{k}":ly.diff(k) for k in (1,5,10,21,63,126,252)})
F["vol21"]=r.rolling(21).std(); F["vol63"]=r.rolling(63).std(); F["dd"]=ly-ly.rolling(252).max(); F["ma_gap"]=ly-ly.rolling(100).mean()
H=21; F["y"]=ly.shift(-H)-ly; D=F.dropna(); X=D.drop(columns="y").values; y=D["y"].values
print("daily rows",len(D),D.index[0].date(),"->",D.index[-1].date())
mk={"ridge":lambda:make_pipeline(StandardScaler(),Ridge(alpha=3000)),
    "gbm":lambda:HistGradientBoostingRegressor(max_depth=3,learning_rate=.03,max_iter=120,min_samples_leaf=60,l2_regularization=10)}
start=len(D)-1260; P={m:[] for m in list(mk)+["zero","drift"]}; A=[]; idx=[]
for s in range(start,len(D),63):
    e=min(s+63,len(D)); tr=slice(0,s-H)             # purge overlap: targets must be known at s
    A+=list(y[s:e]); idx+=list(D.index[s:e])
    for m in mk: P[m]+=list(mk[m]().fit(X[tr],y[tr]).predict(X[s:e]))
    P["zero"]+=[0]*(e-s); P["drift"]+=[y[tr].mean()]*(e-s)
A=np.array(A); rows=[]
for m,v in P.items():
    v=np.array(v); rows.append((m,np.mean(np.abs(np.expm1(v-A)))*100,np.sqrt(np.mean((v-A)**2))*100,(np.sign(v)==np.sign(A)).mean()*100,np.corrcoef(v,A)[0,1] if v.std()>0 else np.nan))
print(pd.DataFrame(rows,columns=["model","MAPE_21d_%","RMSE_%","direction_%","corr"]).round(2).to_string(index=False))
print("share of up months in test:",round((A>0).mean()*100,1))
