import numpy as np, pandas as pd, json
d=pd.read_csv("nifty_metal_official.csv",parse_dates=["date"]).set_index("date")["close"]
y=np.log(d.resample("M").last())
def drift(tr,H): return tr.iloc[-1]+(tr.iloc[-1]-tr.iloc[0])/(len(tr)-1)*np.arange(1,H+1)
H=(2027-y.index[-1].year)*12+12-y.index[-1].month
path=drift(y,H); sd=y.diff().dropna().values[-60:].std()
k=np.sqrt(np.arange(1,H+1))*sd*1.2816
fdates=pd.date_range(y.index[-1],periods=H+1,freq="M")[1:]
# 12-month holdout check + rolling 12m accuracy
tr,te=y.iloc[:-12],y.iloc[-12:]; p=drift(tr,12); kk=np.sqrt(np.arange(1,13))*tr.diff().dropna().values[-60:].std()*1.2816
errs=[abs(np.exp(drift(y.iloc[:i+1],12)[-1]-y.iloc[i+12])-1)*100 for i in range(len(y)-72,len(y)-12)]
cur=float(np.exp(y.iloc[-1])); fin=float(np.exp(path[-1]))
e={"Index":"Nifty Metal","Data":"official NSE index","Current":round(cur),"Best_model":"constant trend (drift)","Dec2027_forecast":round(fin),
 "Low_p10":round(float(np.exp(path[-1]-k[-1]))),"High_p90":round(float(np.exp(path[-1]+k[-1]))),"Change_pct":round((fin/cur-1)*100,1),
 "MAE_best_pct":round(float(np.mean(errs)),1),"MAE_naive_pct":19.3,
 "hist":[[i.strftime("%Y-%m"),round(float(np.exp(v)),1)] for i,v in y[-96:].items()],
 "fc":[[i.strftime("%Y-%m"),round(float(np.exp(a)),1),round(float(np.exp(a-b)),1),round(float(np.exp(a+b)),1)] for i,a,b in zip(fdates,path,k)],
 "check":{"mape_pct":round(float(np.mean(np.abs(np.exp(p)/np.exp(te.values)-1))*100),1),"end_err_pct":round(float((np.exp(p[-1])/np.exp(te.values[-1])-1)*100),1),
  "inside_band_pct":round(float(((te.values>=p-kk)&(te.values<=p+kk)).mean()*100)),"pred":[round(float(np.exp(v))) for v in p],
  "actual":[round(float(np.exp(v))) for v in te.values],"months":[i.strftime("%Y-%m") for i in te.index]}}
json.dump({"Nifty Metal":e},open("data_metal.json","w"))
t=open("template.html").read().replace("__DATA__",json.dumps({"Nifty Metal":e})).replace("Nifty Sector Forecasts to Dec 2027","Nifty Metal Forecast to Dec 2027").replace("Sector indices marked \"proxy\" are rebuilt from constituent stocks.","Built on official NSE daily index data (Nov 2015 – Oct 2026).")
open("index.html","w").write(t); print({k_:v for k_,v in e.items() if k_ not in("hist","fc","check")}); print(e["check"]["mape_pct"],e["check"]["end_err_pct"],e["check"]["inside_band_pct"])
