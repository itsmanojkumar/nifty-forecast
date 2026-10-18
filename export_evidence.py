"""Bridge ML -> frontend: slim stakeholder_evidence.json into frontend/src/data/evidence.json (keys match indices.json)."""
import json, os

KEYS = {"Nifty Metal": "metal", "Nifty 50": "nifty50"}

def export(src="stakeholder_evidence.json", dst="frontend/src/data/evidence.json"):
    d = json.load(open(src))
    out = {}
    for name, v in d.items():
        prod = {h: {k: x for k, x in r.items() if k != "series"} for h, r in v["production"].items()}
        s12 = [{k: r[k] for k in ("origin", "target", "pred", "lo", "hi", "actual", "inside", "err_trend")} for r in v["production"]["12"]["series"]]
        f = v["forecast"]
        out[KEYS[name]] = {"name": name, "source": v["source"], "first": v["first"], "daily_rows": v["daily_rows"], "months": v["months"],
                           "asof": f["asof"], "current": f["current"], "dec2027": f["fc"][-1][1:], "horizons": prod, "backtest12": s12, "ml": v["ml"]}
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(out, open(dst, "w"))
    print("wrote", dst, os.path.getsize(dst), "bytes")

if __name__ == "__main__":
    export()
