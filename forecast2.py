import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, yfinance as yf
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

REAL={"Nifty Pharma":"^CNXPHARMA"}
BASKET={"Nifty Defence":("",["HAL","BEL","BDL","MAZDOCK","COCHINSHIP","BEML","SOLARINDS","DATAPATTNS","MTARTECH","ASTRAMICRO","GRSE","PARAS","BHARATFORG","MIDHANI"])}
def monthly(s): return s.resample("M").last().dropna()
series, anchor, kind = {}, {}, {}
for n,t in REAL.items():
    series[n]=monthly(yf.download(t,start="2007-01-01",auto_adjust=True,progress=False)["Close"].squeeze()); kind[n]="actual index"
for n,(t,cs) in BASKET.items():
    d=yf.download([c+".NS" for c in cs],start="2007-01-01",auto_adjust=True,progress=False)["Close"]
    d=d.dropna(axis=1,thresh=int(len(d)*.5)) if False else d
    r=np.log(d).diff().clip(-.3,.3); idx=np.exp(r.mean(axis=1,skipna=True).fillna(0).cumsum())
    last=100.0
    idx=idx/idx.iloc[-1]*last; series[n]=monthly(idx); kind[n]="constituent proxy"
    print(n,"names with data:",int(d.notna().any().sum()),"/",len(cs))
END=pd.Timestamp("2027-12-31")
def fc(y,h,m):
    if m=="drift": dr=(y.iloc[-1]-y.iloc[0])/(len(y)-1); return y.iloc[-1]+dr*np.arange(1,h+1)
    if m=="ets": return ExponentialSmoothing(y.values,trend="add",damped_trend=True).fit().forecast(h)
    if m=="arima": return ARIMA(y.values,order=(1,1,1),trend="t").fit().forecast(h)
    if m=="rw": return np.repeat(y.iloc[-1],h)
M=["rw","drift","ets","arima"]
rows=[];plots={}
for n,s in series.items():
    y=np.log(s[s.index>=("2010-01-01" if "Pharma" in n else "2018-01-01")]); H=12; err={m:[] for m in M}
    for i in range(max(len(y)-H-84,24),len(y)-H,3):  # expanding-window, 12-mo-ahead, last 7y
        tr,te=y.iloc[:i+1],y.iloc[i+1:i+1+H].values
        for m in M: err[m].append(np.mean(np.abs(fc(tr,H,m)-te)))
    mae={m:np.mean(v) for m,v in err.items()}; best=min(mae,key=mae.get)
    h=(END.year-y.index[-1].year)*12+END.month-y.index[-1].month
    path=fc(y,h,best)
    # bootstrap band from historical monthly log-returns around the model path
    ret=y.diff().dropna().values[-120:]; rng=np.random.default_rng(0)
    sims=rng.choice(ret-ret.mean(),(4000,h)).cumsum(axis=1)
    lo,hi=np.percentile(path[-1]+sims[:,-1],[10,90])
    f=pd.Series(np.exp(path),index=pd.date_range(y.index[-1],periods=h+1,freq="M")[1:])
    cur=s.iloc[-1]
    rows.append(dict(Index=n,Data=kind[n],Current=round(cur),Best_model=best,Dec2027_forecast=round(f.iloc[-1]),
        Low_p10=round(np.exp(lo)),High_p90=round(np.exp(hi)),Change_pct=round((f.iloc[-1]/cur-1)*100,1),
        MAE_best_pct=round((np.exp(mae[best])-1)*100,1),MAE_naive_pct=round((np.exp(mae['rw'])-1)*100,1)))
    plots[n]=(s,f,np.exp(path[-1]+np.percentile(sims,10,axis=0)),np.exp(path[-1]+np.percentile(sims,90,axis=0)) if False else None)
    c=np.percentile(sims,[10,90],axis=0); plots[n]=(s,f,np.exp(path+c[0]),np.exp(path+c[1]))
df=pd.DataFrame(rows); df.to_csv("forecast_pharma_defence.csv",index=False); print(df.to_string(index=False))
fig,ax=plt.subplots(1,2,figsize=(12,4))
for a,(n,(s,f,lo,hi)) in zip(ax.flat,plots.items()):
    a.plot(s[-96:],c="k");a.plot(f,c="C0");a.fill_between(f.index,lo,hi,alpha=.2);a.set_title(n)
plt.tight_layout();plt.savefig("forecast_pharma_defence.png",dpi=110)
