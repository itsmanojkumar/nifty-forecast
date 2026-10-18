import requests, pandas as pd, io
from concurrent.futures import ThreadPoolExecutor
days=pd.bdate_range("2015-01-01","2026-10-16")
def get(d):
    for _ in range(3):
        try:
            r=requests.get(f"https://archives.nseindia.com/content/indices/ind_close_all_{d:%d%m%Y}.csv",headers={"User-Agent":"Mozilla/5.0"},timeout=25)
            if r.status_code==404: return None
            if r.ok:
                x=pd.read_csv(io.StringIO(r.text)); x=x[x["Index Name"].str.strip().str.lower()=="nifty metal"]
                return None if x.empty else (d,float(x["Closing Index Value"].iloc[0]))
        except Exception: pass
    return "fail"
with ThreadPoolExecutor(8) as ex: res=list(ex.map(get,days))
ok=[r for r in res if isinstance(r,tuple)]
print("days",len(days),"got",len(ok),"fail",sum(r=="fail" for r in res))
pd.DataFrame(ok,columns=["date","close"]).to_csv("nifty_metal_official.csv",index=False)
