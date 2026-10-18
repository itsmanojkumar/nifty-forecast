"use client";
import { useMemo, useState } from "react";
import data from "@/data/indices.json";
import { AllData, IndexData, f0, mon, pc } from "@/lib/types";
import { BandChart, CheckChart, ModelsChart } from "./Charts";
import PageNav from "./PageNav";
import { useHashKey } from "@/lib/useHashKey";

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
    const [y, m] = d.hist[d.hist.length - 1][0].split("-");
    const lim = `${+y - range}-${m}`;
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

type TF = { id: string; label: string; kind: "day" | "month"; i: number; err?: number };
const timeframes = (d: IndexData): TF[] => ([
  { id: "1d", label: "1 day", kind: "day", i: 0 },
  { id: "1w", label: "1 week", kind: "day", i: 4 },
  { id: "15d", label: "15 days", kind: "day", i: 14 },
  { id: "1m", label: "1 month", kind: "month", i: 0, err: d.acc[0]?.err },
  { id: "3m", label: "3 months", kind: "month", i: 2, err: d.acc[1]?.err },
  { id: "6m", label: "6 months", kind: "month", i: 5, err: d.acc[2]?.err },
  { id: "1y", label: "1 year", kind: "month", i: 11, err: d.acc[3]?.err },
  { id: "end", label: "Dec 2027", kind: "month", i: d.fc.length - 1 },
] as TF[]).filter((t) => (t.kind === "day" ? t.i < d.short.fc.length : t.i < d.fc.length));

function Timeframes({ d }: { d: IndexData }) {
  const tfs = timeframes(d);
  const [id, setId] = useState("15d");
  const tf = tfs.find((t) => t.id === id) ?? tfs[0];
  const day = tf.kind === "day";
  const f = day ? d.short.fc[tf.i] : d.fc[tf.i];
  const when = day ? `${f[0]} (${tf.i + 1} trading day${tf.i ? "s" : ""})` : mon(f[0]) + " month-end";
  const chg = (f[1] / d.current - 1) * 100;
  const stats: [string, string, string][] = [
    ["Forecast", f0(f[1]), ""],
    ["Change from today", pc(chg), chg >= 0 ? "text-[var(--up)]" : "text-[var(--dn)]"],
    ["Low (10%)", f0(f[2]), ""],
    ["High (90%)", f0(f[3]), ""],
  ];
  return (
    <Card title="Forecast by timeframe" desc="Choose how far ahead to look. The range is where the index should land 8 times in 10.">
      <div role="tablist" aria-label="Timeframe" className="mb-3 flex flex-wrap gap-1.5">
        {tfs.map((t) => (
          <button key={t.id} role="tab" aria-selected={t.id === tf.id} onClick={() => setId(t.id)}
            className={`rounded-lg border px-3 py-1 text-[13px] ${t.id === tf.id ? "border-[var(--acc)] bg-[var(--acc)] text-white" : "border-[var(--bd)] hover:border-[var(--acc)]"}`}>{t.label}</button>
        ))}
      </div>
      <p className="m-0 mb-2 text-sm">Target: <b>{when}</b>{tf.err != null && <span className="text-[var(--mut)]"> · past error at this horizon ≈ ±{tf.err}%</span>}</p>
      <div className="mb-3 grid grid-cols-[repeat(auto-fit,minmax(140px,1fr))] gap-2.5">
        {stats.map(([l, v, c]) => (
          <div key={l} className="rounded-xl bg-[var(--bg)] px-3 py-2.5"><small className="block text-xs text-[var(--mut)]">{l}</small><b className={`text-xl tabular-nums ${c}`}>{v}</b></div>
        ))}
      </div>
      {day
        ? <BandChart hist={d.short.hist} fc={d.short.fc.slice(0, tf.i + 1)} label={(s) => s} height={280} dots />
        : <BandChart hist={d.hist.slice(-Math.max(24, tf.i + 13))} fc={d.fc.slice(0, tf.i + 1)} label={mon} height={280} />}
    </Card>
  );
}

function FifteenDay({ d }: { d: IndexData }) {
  const prev = d.short.hist[d.short.hist.length - 1];
  return (
    <Card title="15-day forecast, day by day" desc={`From the close of ${prev[0]} (${f0(prev[1])}). Weekdays only; exchange holidays are not removed yet.`}>
      {d.short_meta ? (
        <div className="mb-3 grid gap-2.5 sm:grid-cols-3">
          <div className="rounded-xl bg-[var(--bg)] px-3 py-2.5"><small className="block text-xs text-[var(--mut)]">Overnight US markets</small>
            <b className="tabular-nums">S&amp;P 500 {pc(d.short_meta.overnight_pct.spx)} · Nasdaq {pc(d.short_meta.overnight_pct.ndx)}</b></div>
          <div className="rounded-xl bg-[var(--bg)] px-3 py-2.5"><small className="block text-xs text-[var(--mut)]">Model&apos;s day-1 move ({d.short_meta.made_for})</small>
            <b className={`tabular-nums ${d.short_meta.day1_return_pct >= 0 ? "text-[var(--up)]" : "text-[var(--dn)]"}`}>{pc(d.short_meta.day1_return_pct)}</b></div>
          <div className="rounded-xl bg-[var(--bg)] px-3 py-2.5"><small className="block text-xs text-[var(--mut)]">India VIX (sets the range)</small>
            <b className="tabular-nums">{d.short_meta.india_vix.toFixed(1)}</b></div>
        </div>
      ) : null}
      <p className="m-0 mb-3 text-[12.5px] text-[var(--mut)]">
        {d.short_meta
          ? "Day 1 comes from a model of overnight global markets, which cut next-day error by 6.5% in a 2022–26 backtest. Later days add the average daily drift; direction beyond day 1 is close to a coin flip, so read the range."
          : "The daily direction is close to a coin flip, so read the range, not the line."}
      </p>
      <div className="max-h-[420px] overflow-auto">
        <table className="w-full border-collapse text-sm tabular-nums">
          <thead className="sticky top-0 bg-[var(--card)]"><tr className="text-xs uppercase text-[var(--mut)]">
            {["Day", "Date", "Forecast", "Change", "Low (10%)", "High (90%)", "Range width"].map((h, i) => <th key={h} className={`whitespace-nowrap p-2 font-medium ${i > 1 ? "text-right" : "text-left"}`}>{h}</th>)}
          </tr></thead>
          <tbody>{d.short.fc.map((f, i) => {
            const chg = (f[1] / d.current - 1) * 100;
            return (
              <tr key={f[0]} className="border-t border-[var(--bd)]">
                <td className="p-2 text-[var(--mut)]">{i + 1}</td><td className="p-2">{f[0]}</td>
                <td className="p-2 text-right font-semibold">{f0(f[1])}</td>
                <td className={`p-2 text-right ${chg >= 0 ? "text-[var(--up)]" : "text-[var(--dn)]"}`}>{pc(chg)}</td>
                <td className="p-2 text-right">{f0(f[2])}</td><td className="p-2 text-right">{f0(f[3])}</td>
                <td className="p-2 text-right text-[var(--mut)]">±{(((f[3] - f[2]) / 2 / f[1]) * 100).toFixed(1)}%</td>
              </tr>);
          })}</tbody>
        </table>
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const [key, pick] = useHashKey(KEYS);
  const d = ALL[key];
  return (
    <>
      <header className="bg-[image:var(--hero)] px-4 pb-[70px] pt-7 text-white">
        <div className="mx-auto max-w-[1080px]">
          <PageNav active="/forecast" indexKey={key} />
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
        <Timeframes d={d} />
        <LongChart d={d} />
        <FifteenDay d={d} />
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
