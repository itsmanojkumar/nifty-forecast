"""Build index.html (Nifty Metal dashboard) from template_metal.html + data_metal.json (run build_metal.py first)."""
import json, pandas as pd

e = json.load(open("data_metal.json"))["Nifty Metal"]
m = pd.read_csv("nifty_metal_official.csv", parse_dates=["date"]).set_index("date")["close"].resample("M").last()
out = {
    "asof": "16 Oct 2026", "current": e["Current"],
    "hist": [[i.strftime("%Y-%m"), round(float(v), 1)] for i, v in m.items()],
    "fc": e["fc"], "check": e["check"],
    "acc": [{"h": "1 month", "err": 5.4, "dir": 60}, {"h": "3 months", "err": 10.3, "dir": 68},
            {"h": "6 months", "err": 13.5, "dir": 76}, {"h": "12 months", "err": 17.4, "dir": 82}],
    "models": [["Trend (winner)", 17.4], ["No change", 19.3], ["ARIMA", 19.3], ["Smoothing", 20.4], ["Ridge ML", 22.3], ["Boosting ML", 26.2]],
}
json.dump(out, open("data_metal_ui.json", "w"))
open("index.html", "w", encoding="utf-8").write(open("template_metal.html", encoding="utf-8").read().replace("__DATA__", json.dumps(out)))
print("built index.html", len(out["hist"]), "hist months,", len(out["fc"]), "forecast months")
