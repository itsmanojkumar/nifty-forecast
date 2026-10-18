import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
d=pd.read_csv("nifty_metal_official.csv",parse_dates=["date"]).set_index("date")["close"]
y=np.log(d.resample("M").last()); print("monthly obs",len(y),y.index[0].date(),"->",y.index[-1].date(),"last",round(np.exp(y.iloc[-1])))
def stat(tr,H,m):
    if m=="rw": return np.repeat(tr.iloc[-1],H)
    if m=="drift": return tr.iloc[-1]+(tr.iloc[-1]-tr.iloc[0])/(len(tr)-1)*np.arange(1,H+1)
    if m=="ets": return ExponentialSmoothing(tr.values,trend="add",damped_trend=True).fit().forecast(H)
    if m=="arima": return ARIMA(tr.values,order=(1,1,1),trend="t").fit().forecast(H)
def mlfeat(s):  # s: log price series up to t
    r=s.diff().dropna().values
    return [r[-1],r[-3:].sum(),r[-6:].sum(),r[-12:].sum(),r[-12:].std(),r[-24:].sum(),s.iloc[-1]-s.iloc[-24:].mean()]
def ml(tr,H,kind):
    X,t=[],[]
    for i in range(30,len(tr)-H): X.append(mlfeat(tr.iloc[:i+1])); t.append(tr.iloc[i+H]-tr.iloc[i])
    m=Ridge(alpha=10) if kind=="ridge" else GradientBoostingRegressor(n_estimators=80,max_depth=2,learning_rate=.05,subsample=.8,random_state=0)
    m.fit(np.array(X),t); return tr.iloc[-1]+m.predict([mlfeat(tr)])[0]
M=["rw","drift","ets","arima","ridge","gbm"]; rows=[]
n0=len(y)-72
for H in (3,6,12):
    for i in range(n0,len(y)-H):
        tr=y.iloc[:i+1]; a=y.iloc[i+H]; b=tr.iloc[-1]
        for m in M:
            p=ml(tr,H,m) if m in("ridge","gbm") else stat(tr,H,m)[-1]
            rows.append((H,m,abs(np.exp(p-a)-1)*100,np.sign(p-b)==np.sign(a-b)))
df=pd.DataFrame(rows,columns=["H","model","MAPE_%","direction"])
t=df.groupby(["H","model"]).agg(MAPE=("MAPE_%","mean"),direction=("direction","mean")).round(3).unstack(0)
print(t.to_string())
# forecast to Dec 2027
Hf=(2027-y.index[-1].year)*12+12-y.index[-1].month
best=df[df.H==12].groupby("model")["MAPE_%"].mean().idxmin(); print("best 12m model:",best,"horizon months",Hf)
path=ml(y,Hf,best) if best in("ridge","gbm") else stat(y,Hf,best)[-1]
sd=y.diff().dropna().values[-60:].std()*np.sqrt(Hf)
print("Dec2027 forecast",round(np.exp(path)),"80% range",round(np.exp(path-1.2816*sd)),round(np.exp(path+1.2816*sd)),f"({(np.exp(path)/np.exp(y.iloc[-1])-1)*100:+.1f}%)")
