"""Week 1: Python for ML & data preprocessing on the official Nifty Metal daily index data."""
import numpy as np, pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
raw=pd.read_csv("nifty_metal_official.csv")
log={}
log["rows_raw"]=len(raw); log["dtypes_before"]=str(dict(raw.dtypes.astype(str)))
log["missing_values"]=int(raw.isna().sum().sum()); log["duplicate_dates"]=int(raw.duplicated("date").sum())
df=raw.drop_duplicates("date").copy(); df["date"]=pd.to_datetime(df["date"]); df=df.sort_values("date").set_index("date")
gaps=df.index.to_series().diff().dt.days; log["gaps_over_5_days"]=int((gaps>5).sum()); log["max_gap_days"]=int(gaps.max())
df["ret"]=np.log(df.close).diff()                                    # feature: daily log return
z=(df.ret-df.ret.mean())/df.ret.std(); log["outliers_|z|>4"]=int((z.abs()>4).sum())
df["ret_clipped"]=df.ret.clip(df.ret.quantile(.001),df.ret.quantile(.999))   # winsorise extremes
df["ma20"]=df.close.rolling(20).mean(); df["vol20"]=df.ret.rolling(20).std(); df["mom60"]=df.close.pct_change(60)
df["month"]=df.index.month_name(); df["weekday"]=df.index.day_name()
df["regime"]=np.where(df.vol20>df.vol20.median(),"high_vol","low_vol")
df=df.dropna(); enc=pd.get_dummies(df,columns=["weekday","regime"],drop_first=True)   # encode categoricals
num=["ret_clipped","ma20","vol20","mom60"]
std=StandardScaler().fit_transform(enc[num]); mm=MinMaxScaler().fit_transform(enc[num])
log["rows_clean"]=len(enc); log["columns_after_encoding"]=list(enc.columns)
log["scaled_mean_std"]=[round(float(std.mean()),3),round(float(std.std()),3)]; log["minmax_range"]=[float(mm.min()),float(mm.max())]
eda=df.close.describe().round(1).to_dict(); log["close_summary"]=eda
log["ann_return_%"]=round(float(df.ret.mean()*252*100),1); log["ann_vol_%"]=round(float(df.ret.std()*np.sqrt(252)*100),1)
log["worst_day_%"]=round(float(np.expm1(df.ret.min())*100),1); log["best_day_%"]=round(float(np.expm1(df.ret.max())*100),1)
log["corr_ret_vs_mom60"]=round(float(df.ret.corr(df.mom60)),3)
log["avg_ret_by_weekday_%"]={k:round(v*100,3) for k,v in df.groupby("weekday").ret.mean().items()}
log["avg_ret_by_regime_%"]={k:round(v*100,3) for k,v in df.groupby("regime").ret.mean().items()}
enc.to_csv("nifty_metal_clean.csv"); import json; json.dump(log,open("week1_log.json","w"),indent=1,default=str); print(json.dumps(log,indent=1,default=str))
