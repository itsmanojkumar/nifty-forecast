"""Download NSE F&O daily bhavcopies and keep one row per day of NIFTY options/futures aggregates.

Output: data/nifty_options_daily.csv (resumable; rerun to continue or to add new days).
Columns: date, put_oi, call_oi, put_vol, call_vol, pcr_oi, pcr_vol, near_pcr_oi, put_oi_chg, call_oi_chg,
         fut_close, fut_oi, fut_oi_chg   (all end-of-day for that date)
"""
import io, os, sys, time, zipfile, threading
from concurrent.futures import ThreadPoolExecutor
import pandas as pd, requests

OUT = "data/nifty_options_daily.csv"
NEW_FORMAT_FROM = pd.Timestamp("2024-07-08")
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
       "Accept": "*/*", "Referer": "https://www.nseindia.com/"}
lock = threading.Lock()

def url(d, new):
    if new:
        return f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"
    mon = d.strftime("%b").upper()
    return f"https://nsearchives.nseindia.com/content/historical/DERIVATIVES/{d:%Y}/{mon}/fo{d:%d}{mon}{d:%Y}bhav.csv.zip"

def normalise(df, new):
    if new:
        df = df[df.TckrSymb == "NIFTY"]
        return pd.DataFrame({"kind": df.FinInstrmTp.map({"IDO": "OPT", "IDF": "FUT"}), "typ": df.OptnTp, "expiry": pd.to_datetime(df.XpryDt),
                             "close": df.ClsPric, "oi": df.OpnIntrst, "oi_chg": df.ChngInOpnIntrst, "vol": df.TtlTradgVol})
    df = df[df.SYMBOL == "NIFTY"]
    return pd.DataFrame({"kind": df.INSTRUMENT.map({"OPTIDX": "OPT", "FUTIDX": "FUT"}), "typ": df.OPTION_TYP, "expiry": pd.to_datetime(df.EXPIRY_DT, format="%d-%b-%Y"),
                         "close": df.CLOSE, "oi": df.OPEN_INT, "oi_chg": df.CHG_IN_OI, "vol": df.CONTRACTS})

def aggregate(d, x):
    o, f = x[x.kind == "OPT"], x[x.kind == "FUT"].sort_values("expiry")
    p, c = o[o.typ == "PE"], o[o.typ == "CE"]
    near = o[o.expiry == o.expiry.min()]
    np_, nc = near[near.typ == "PE"].oi.sum(), near[near.typ == "CE"].oi.sum()
    return dict(date=d.strftime("%Y-%m-%d"), put_oi=p.oi.sum(), call_oi=c.oi.sum(), put_vol=p.vol.sum(), call_vol=c.vol.sum(),
                pcr_oi=p.oi.sum() / max(c.oi.sum(), 1), pcr_vol=p.vol.sum() / max(c.vol.sum(), 1), near_pcr_oi=np_ / max(nc, 1),
                put_oi_chg=p.oi_chg.sum(), call_oi_chg=c.oi_chg.sum(),
                fut_close=f.close.iloc[0] if len(f) else None, fut_oi=f.oi.sum(), fut_oi_chg=f.oi_chg.sum())

def fetch(d):
    for new in ([True, False] if d >= NEW_FORMAT_FROM else [False, True]):
        for attempt in range(3):
            try:
                r = requests.get(url(d, new), headers=HDR, timeout=40)
                if r.status_code == 404: break                      # holiday / wrong format
                r.raise_for_status()
                z = zipfile.ZipFile(io.BytesIO(r.content))
                df = pd.read_csv(z.open(z.namelist()[0]), low_memory=False)
                df.columns = [c.strip() for c in df.columns]
                return aggregate(d, normalise(df, new))
            except Exception:
                time.sleep(2 + 3 * attempt)
    return None

def main(start="2016-01-01", end=None):
    os.makedirs("data", exist_ok=True)
    done = set(pd.read_csv(OUT).date) if os.path.exists(OUT) else set()
    days = [d for d in pd.bdate_range(start, end or pd.Timestamp.today().normalize()) if d.strftime("%Y-%m-%d") not in done]
    print(f"{len(done)} days cached, {len(days)} to try", flush=True)
    rows, n = [], 0
    def save():
        nonlocal rows
        if rows:
            pd.DataFrame(rows).to_csv(OUT, mode="a", header=not os.path.exists(OUT), index=False); rows = []
    with ThreadPoolExecutor(4) as ex:
        for d, row in zip(days, ex.map(fetch, days)):
            n += 1
            if row:
                with lock: rows.append(row)
            if n % 100 == 0:
                save(); print(f"{n}/{len(days)} through {d:%Y-%m-%d}", flush=True)
    save()
    df = pd.read_csv(OUT).drop_duplicates("date").sort_values("date"); df.to_csv(OUT, index=False)
    print("rows", len(df), df.date.min(), "->", df.date.max())

if __name__ == "__main__":
    main(*sys.argv[1:])
