"use client";
import { useEffect, useMemo, useState } from "react";
import data from "@/data/indices.json";
import { AllData, IndexData, f0, mon, pc } from "@/lib/types";
import { BandChart, CheckChart, ModelsChart } from "./Charts";

const ALL = data as unknown as AllData;
const KEYS = Object.keys(ALL);

const Card = ({ title, desc, children }: { title: string; desc?: string; children: React.ReactNode }) => (
  <section className="mb-4 rounded-2xl border border-[var(--bd)] bg-[var(--card)] p-[18px]">
    <h2 className="m-0 text-[17px] font-semibold">{title}</h2>
    {desc && <p className="mb-3 mt-0.5 text-[13px] text-[var(--mut)]">{desc}</p>}
    {children}
  </section>
);

function Kpis({ d }: { d: IndexData }) {
  const fin = d.fc[d.fc.length - 1], cur = d.current, up = fin[1] >= cur;
  const items = [
    { l: "Index today", v: f0(cur), s: `as of ${d.asof}`, c: "" },
    { l: "Dec 2027 forecast", v: f0(fin[1]), s: `${pc((fin[1] / cur - 1) * 100)} from today`, c: up ? "text-[var(--up)]" : "text-[var(--dn)]" },
    { l: "80% range", v: `${f0(fin[2])} – ${f0(fin[3])}`, s: `${pc((fin[2] / cur - 1) * 100)} to ${pc((fin[3] / cur - 1) * 100)}`, c: "" },
    { l: "12-month accuracy", v: `≈ ${Math.round(100 - d.acc[3].err)}%`, s: `average error ${d.acc[3].err}%`, c: "" },
  ];
  return (
    <div className="mb-4 grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-3">
      {items.map((k) => (
        <div key={k.l} className="rounded-2xl border border-[var(--bd)] bg-[var(--card)] px-4 py-3.5 shadow-[0_4px_18px_#0f172a14]">
          <small className="text-xs uppercase tracking-wide text-[var(--mut)]">{k.l}</small>
          <b className="block text-[26px] tracking-tight">{k.v}</b>
          <span className={`text-[13px] ${k.c || "text-[var(--mut)]"}`}>{k.s}</span>
        </div>
      ))}
    </div>
  );
}

function LongChart({ d }: { d: IndexData }) {
  const [range, setRange] = useState(5);
  const hist = useMemo(() => {
    if (!range) return d.hist;
    const lim = new Date(Date.now() - range * 365.25 * 864e5).toISOString().slice(0, 7);
    return d.hist.filter((x) => x[0] >= lim);
  }, [d, range]);
  return (
    <Card title="Index history and forecast" desc="Grey is the actual index. The blue line is the forecast and the shaded area is the 80% range.">
      <div className="mb-2.5 flex flex-wrap gap-1.5">
        {([["1Y", 1], ["3Y", 3], ["5Y", 5], ["All", 0]] as const).map(([t, v]) => (
          <button key={t} onClick={() => setRange(v)} className={`rounded-lg border px-3 py-1 text-[13px] ${range === v ? "border-[var(--acc)] bg-[var(--acc)] text-white" : "border-[var(--bd)]"}`}>{t}</button>
        ))}
      </div>
      <BandChart hist={hist} fc={d.fc} label={mon} />
    </Card>
  );
}

function MonthPicker({ d }: { d: IndexData }) {
  const [i, setI] = useState(d.fc.length - 1);
  const f = d.fc[i];
  return (
    <Card title="Pick a month" desc="Drag to see the forecast for any month up to Dec 2027.">
      <div className="flex flex-wrap items-center gap-3.5">
        <b className="min-w-[90px]">{mon(f[0])}</b>
        <input type="range" min={0} max={d.fc.length - 1} value={i} onChange={(e) => setI(+e.target.value)} className="min-w-[200px] flex-1 accent-[var(--acc)]" />
      </div>
      <div className="mt-3 grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-2.5">
        {[["Forecast", f0(f[1]), ""], ["Change from today", pc((f[1] / d.current - 1) * 100), f[1] >= d.current ? "text-[var(--up)]" : "text-[var(--dn)]"], ["Low (10%)", f0(f[2]), ""], ["High (90%)", f0(f[3]), ""]].map(([l, v, c]) => (
          <div key={l} className="rounded-xl bg-[var(--bg)] px-3 py-2.5"><small className="block text-xs text-[var(--mut)]">{l}</small><b className={`text-xl ${c}`}>{v}</b></div>
        ))}
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const [key, setKey] = useState(KEYS[0]);
  useEffect(() => { const h = window.location.hash.slice(1); if (ALL[h]) setKey(h); }, []);
  const d = ALL[key];
  const S = d.short, e = S.fc[S.fc.length - 1];
  const pick = (k: string) => { setKey(k); window.history.replaceState(null, "", "#" + k); };
  return (
    <>
      <header className="bg-[image:var(--hero)] px-4 pb-[70px] pt-7 text-white">
        <div className="mx-auto max-w-[1080px]">
          <div className="mb-3.5 inline-flex gap-0.5 rounded-[10px] bg-white/10 p-[3px]">
            {KEYS.map((k) => (
              <button key={k} onClick={() => pick(k)} className={`rounded-lg px-4 py-1.5 text-sm ${k === key ? "bg-white font-semibold text-slate-900" : "text-[#d6e4f0]"}`}>{ALL[k].name}</button>
            ))}
          </div>
          <div><span className="mb-2.5 inline-block rounded-full border border-white/35 px-2.5 py-0.5 text-xs text-[#d6e4f0]">{d.tag}</span></div>
          <h1 className="m-0 text-[26px] tracking-tight">{d.name} Forecast</h1>
          <p className="mt-1 max-w-[640px] text-[#b6c8d8]">Where the {d.name} index may be by Dec 2027, and how much to trust that number.</p>
        </div>
      </header>
      <main key={key} className="mx-auto -mt-12 max-w-[1080px] px-4 pb-12">
        <Kpis d={d} />
        <LongChart d={d} />
        <Card title="Next 15 trading days" desc="Daily forecast from the last 30 closes. Weekdays only; exchange holidays are not removed. The range widens each day.">
          <BandChart hist={S.hist} fc={S.fc} label={(s) => s} height={300} dots />
          <p className="mt-2.5 border-l-[3px] border-[var(--acc2)] pl-2.5 text-[12.5px] text-[var(--mut)]">
            Tomorrow ({S.fc[0][0]}): {f0(S.fc[0][1])} ({f0(S.fc[0][2])} – {f0(S.fc[0][3])}). In 15 days ({e[0]}): {f0(e[1])} ({f0(e[2])} – {f0(e[3])}). Direction is close to a coin flip.
          </p>
        </Card>
        <MonthPicker d={d} />
        <div className="grid gap-4 md:grid-cols-2">
          <Card title="How accurate is it?" desc="Average error of the forecast, tested month by month over the last 6 years.">
            <table className="w-full border-collapse text-sm">
              <thead><tr className="text-xs uppercase text-[var(--mut)]"><th className="p-2 text-left font-medium">Horizon</th><th className="p-2 text-right font-medium">Avg error</th><th className="p-2 text-right font-medium">Accuracy</th><th className="p-2 text-right font-medium">Direction</th></tr></thead>
              <tbody>{d.acc.map((a) => (
                <tr key={a.h} className="border-t border-[var(--bd)]"><td className="p-2">{a.h}</td><td className="p-2 text-right">{a.err}%</td>
                  <td className="p-2"><div className="ml-auto h-2 min-w-[90px] overflow-hidden rounded-full bg-[var(--bd)]"><i className="block h-full bg-[var(--acc)]" style={{ width: `${100 - a.err}%` }} /></div></td>
                  <td className="p-2 text-right">{a.dir}%</td></tr>
              ))}</tbody>
            </table>
            <p className="mt-2.5 border-l-[3px] border-[var(--acc2)] pl-2.5 text-[12.5px] text-[var(--mut)]">Direction accuracy looks high because the index rose most of the time. It is not timing skill.</p>
          </Card>
          <Card title="Models compared (12 months)" desc={d.modelNote}><ModelsChart models={d.models} /></Card>
        </div>
        <Card title="Check: forecast made 12 months ago vs. actual" desc={`Average error ${d.check.mape_pct}%, error at month 12 ${pc(d.check.end_err_pct)}, ${d.check.inside_band_pct}% of months inside the 80% range. One test window only.`}>
          <CheckChart check={d.check} />
        </Card>
        <Card title="What this means">
          <p className="m-0 mb-2">{d.note1}</p>
          <p className="m-0">{d.note2}</p>
        </Card>
      </main>
      <footer className="px-4 pb-8 pt-2 text-center text-[12.5px] text-[var(--mut)]">
        Statistical exercise, not investment advice. Code and data:{" "}
        <a className="text-[var(--acc)]" href="https://github.com/itsmanojkumar/nifty-forecast">github.com/itsmanojkumar/nifty-forecast</a>
      </footer>
    </>
  );
}
