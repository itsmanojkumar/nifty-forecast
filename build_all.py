"""Build combined index.html with a Nifty Metal / Nifty 50 switcher from template_metal.html + data json files."""
import json, re
t = open("template_metal.html", encoding="utf-8").read()
def sub(a, b):
    global t
    assert a in t, a[:50]
    t = t.replace(a, b, 1)
sub('<span class="tag">Official NSE index data · Nov 2015 – Oct 2026</span><h1>Nifty Metal Forecast</h1><p>Where the Nifty Metal index may be by Dec 2027, and how much to trust that number.</p>',
    '<div class="sw" id="sw"></div><span class="tag" id="tag"></span><h1 id="ttl"></h1><p id="lead"></p>')
sub('<title>Nifty Metal Forecast</title>', '<title>Nifty Forecasts</title>')
sub('.hero h1{', '.sw{display:inline-flex;background:#ffffff1f;border-radius:10px;padding:3px;margin-bottom:14px;gap:2px}.sw button{border:0;background:transparent;color:#d6e4f0;padding:6px 16px;border-radius:8px;font:inherit;font-size:14px;cursor:pointer}.sw button.on{background:#fff;color:#0f172a;font-weight:600}.hero h1{')
sub('<p class="d">Lower error is better. The simple trend won; ML models did worse.</p>', '<p class="d" id="mn"></p>')
m = re.search(r'<p style="margin:0 0 8px">.*?</p>\n<p style="margin:0">.*?</p>', t, re.S)
t = t.replace(m.group(0), '<p style="margin:0 0 8px" id="n1"></p><p style="margin:0" id="n2"></p>', 1)
# turn the script into a render(D) function
i = t.index("<script>\nconst D=__DATA__,")
head = t[:i]; js = t[i + len("<script>\n"):]
js = js.replace("const D=__DATA__,css=", "const css=", 1)
first_nl = js.index("\n"); defs, body = js[:first_nl + 1], js[first_nl + 1:]
body = body.replace("</script></body></html>", "").rstrip()
body = body.replace('const rb=document.getElementById("rng");', 'const rb=document.getElementById("rng");rb.innerHTML="";', 1)
pre = '''["c","s","m","h"].forEach(id=>{const x=Chart.getChart(id);x&&x.destroy()});
document.getElementById("tag").textContent=D.tag;document.getElementById("ttl").textContent=D.name+" Forecast";document.getElementById("lead").textContent="Where the "+D.name+" index may be by Dec 2027, and how much to trust that number.";
document.getElementById("mn").textContent=D.modelNote;document.getElementById("n1").textContent=D.note1;document.getElementById("n2").textContent=D.note2;document.title=D.name+" Forecast";
'''
tail = '''
const ALL=__ALL__;let key="metal";
function setup(){const sw=document.getElementById("sw");sw.innerHTML="";Object.entries(ALL).forEach(([k,v])=>{const b=document.createElement("button");b.textContent=v.name;b.className=k==key?"on":"";b.onclick=()=>{key=k;location.hash=k;setup()};sw.append(b)});render(ALL[key])}
const h0=location.hash.slice(1);if(ALL[h0])key=h0;setup();
</script></body></html>'''
t = head + "<script>\n" + defs + "function render(D){\n" + pre + body + "\n}" + tail
metal = json.load(open("data_metal_ui.json")); n50 = json.load(open("data_nifty50.json"))
metal.update(name="Nifty Metal", tag="Official NSE index data · Nov 2015 – Oct 2026",
    modelNote="Lower error is better. The simple trend won; ML models did worse.",
    note1="The forecast is the long-run upward trend carried forward. Past prices alone could not predict next month's move: Ridge and gradient boosting models scored about the same as guessing on direction. Treat the Dec 2027 number as a central scenario inside a wide range, and expect a typical error of roughly ±17%.",
    note2="I also tested adding copper, aluminium, crude, gold, USD/INR, the dollar index, S&P 500, China and Nifty 50. None of them improved the forecast in a walk-forward test, so they are not used.")
n50.update(name="Nifty 50", tag="Index data from Yahoo Finance · Sep 2007 – Oct 2026",
    modelNote="Lower error is better. The trend model won; differences between models are small.",
    note1=f"The forecast is the long-run upward trend carried forward. Past prices gave little edge over assuming no change beyond that trend. Treat the Dec 2027 number as a central scenario, with a typical error of roughly ±{n50['acc'][3]['err']:.0f}%.",
    note2="Last year's 12-month forecast came in too low because the market rose faster than the trend, so treat the central value as conservative.")
open("index.html", "w", encoding="utf-8").write(t.replace("__ALL__", json.dumps({"metal": metal, "nifty50": n50})))
import os
os.makedirs("frontend/src/data",exist_ok=True)
json.dump({"metal":metal,"nifty50":n50},open("frontend/src/data/indices.json","w"))
print("built index.html and frontend/src/data/indices.json")
