import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, yfinance as yf
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

REAL={"Nifty 50":"^NSEI","Nifty Bank":"^NSEBANK","Nifty IT":"^CNXIT","Nifty Pharma":"^CNXPHARMA"}
BASKET={ # constituent proxies (equal-weight), anchored to latest published index level
 "Nifty Metal":("^CNXMETAL",["TATASTEEL","HINDALCO","JSWSTEEL","VEDL","ADANIENT","JINDALSTEL","NMDC","SAIL","APLAPOLLO","NATIONALUM","HINDZINC","JSL","WELCORP","RATNAMANI"]),
 "Nifty Auto":("^CNXAUTO",["MARUTI","M&M","BAJAJ-AUTO","EICHERMOT","HEROMOTOCO","TVSMOTOR","ASHOKLEY","BOSCHLTD","MRF","BHARATFORG","BALKRISIND","APOLLOTYRE"]),
 "Nifty FMCG":("^CNXFMCG",["HINDUNILVR","ITC","NESTLEIND","BRITANNIA","TATACONSUM","DABUR","GODREJCP","MARICO","COLPAL","UBL","EMAMILTD"]),
 "Nifty Energy":("^CNXENERGY",["RELIANCE","NTPC","POWERGRID","ONGC","COALINDIA","BPCL","IOC","GAIL","TATAPOWER","HINDPETRO","OIL","PETRONET"]),
 "Nifty Realty":("^CNXREALTY",["DLF","GODREJPROP","OBEROIRLTY","PRESTIGE","BRIGADE","SOBHA","PHOENIXLTD"]),
 "Nifty PSU Bank":("^CNXPSUBANK",["SBIN","BANKBARODA","PNB","CANBK","UNIONBANK","INDIANB","BANKINDIA","IOB","UCOBANK","MAHABANK"]),
 "Nifty Media":("^CNXMEDIA",["ZEEL","SUNTV","PVRINOX","NETWORK18","TV18BRDCST","NAZARA","SAREGAMA","DBCORP"]),
 "Nifty Infra":("^CNXINFRA",["LT","RELIANCE","BHARTIARTL","ULTRACEMCO","POWERGRID","NTPC","ADANIPORTS","GRASIM","DLF","CONCOR","INDIGO"]),
}
def monthly(s): return s.resample("M").last().dropna()
series, anchor, kind = {}, {}, {}
for n,t in REAL.items():
    series[n]=monthly(yf.download(t,start="2007-01-01",auto_adjust=True,progress=False)["Close"].squeeze()); kind[n]="actual index"
for n,(t,cs) in BASKET.items():
    d=yf.download([c+".NS" for c in cs],start="2007-01-01",auto_adjust=True,progress=False)["Close"]
    d=d.dropna(axis=1,thresh=int(len(d)*.5)) if False else d
    r=np.log(d).diff().clip(-.3,.3); idx=np.exp(r.mean(axis=1,skipna=True).fillna(0).cumsum())
    last=yf.Ticker(t).history(period="1d")["Close"].iloc[-1]
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
    y=np.log(s[s.index>="2010-01-01"]); H=12; err={m:[] for m in M}
    for i in range(len(y)-H-84,len(y)-H,3):  # expanding-window, 12-mo-ahead, last 7y
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
df=pd.DataFrame(rows); df.to_csv("forecast_dec2027.csv",index=False); print(df.to_string(index=False))
fig,ax=plt.subplots(4,3,figsize=(16,14))
for a,(n,(s,f,lo,hi)) in zip(ax.flat,plots.items()):
    a.plot(s[-96:],c="k");a.plot(f,c="C0");a.fill_between(f.index,lo,hi,alpha=.2);a.set_title(n)
plt.tight_layout();plt.savefig("forecasts.png",dpi=110)

# ---- export for frontend + holdout check (forecast made 12 months ago vs what happened)
import json
out={}
for r_ in rows:
    n=r_["Index"]; s,f,lo,hi=plots[n]; y=np.log(s[s.index>="2010-01-01"]); H=12
    tr,te=y.iloc[:-H],y.iloc[-H:]; pth=fc(tr,H,r_["Best_model"])
    ret=tr.diff().dropna().values[-120:]; sims=np.random.default_rng(1).choice(ret-ret.mean(),(4000,H)).cumsum(1)
    c=np.percentile(sims,[10,90],axis=0)
    inside=((te.values>=pth+c[0])&(te.values<=pth+c[1])).mean()
    out[n]={**r_,"hist":[[d.strftime("%Y-%m"),round(float(v),1)] for d,v in s[-96:].items()],
      "fc":[[d.strftime("%Y-%m"),round(float(a),1),round(float(b),1),round(float(c_),1)] for d,a,b,c_ in zip(f.index,f.values,lo,hi)],
      "check":{"mape_pct":round(float(np.mean(np.abs(np.exp(pth)/np.exp(te.values)-1))*100),1),
               "end_err_pct":round(float((np.exp(pth[-1])/np.exp(te.values[-1])-1)*100),1),
               "inside_band_pct":round(float(inside*100)),
               "pred":[round(float(v)) for v in np.exp(pth)],"actual":[round(float(v)) for v in np.exp(te.values)],
               "months":[d.strftime("%Y-%m") for d in te.index]}}
json.dump(out,open("data.json","w"))
print({k:(v["check"]["mape_pct"],v["check"]["end_err_pct"],v["check"]["inside_band_pct"]) for k,v in out.items()})
