"use client";
import ev from "@/data/evidence.json";
import { AllEvidence, Evidence as E, f0 } from "@/lib/types";
import PageNav from "./PageNav";
import { useHashKey } from "@/lib/useHashKey";
import { BacktestChart, PairBars, PredActualScatter, SkillChart } from "./EvidenceCharts";

const ALL = ev as unknown as AllEvidence;
const KEYS = Object.keys(ALL);
const H = ["1", "3", "6", "12"] as const;
const pv = (p: number | null) => (p == null ? "—" : p < 0.001 ? "< 0.001" : p.toFixed(2));
const sg = (v: number) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(1) + "%";

const Card = ({ title, desc, children, className = "" }: { title: string; desc?: string; children: React.ReactNode; className?: string }) => (
  <section className={`rounded-2xl border border-[var(--bd)] bg-[var(--card)] p-[18px] ${className}`}>
    <h2 className="m-0 text-[17px] font-semibold">{title}</h2>
    {desc && <p className="mb-3 mt-0.5 text-[13px] text-[var(--mut)]">{desc}</p>}
    {children}
  </section>
);

const Pill = ({ tone, children }: { tone: "ok" | "warn" | "bad"; children: React.ReactNode }) => {
  const c = tone === "ok" ? "text-[var(--up)]" : tone === "bad" ? "text-[var(--dn)]" : "text-[var(--acc2)]";
  return <span className={`inline-flex items-center gap-1.5 text-xs font-semibold ${c}`}><i className="h-2 w-2 rounded-full bg-current" />{children}</span>;
};

function Kpis({ d }: { d: E }) {
  const h12 = d.horizons["12"];
  const ml = d.ml.table.filter((r) => !["Trend", "No change"].includes(r.model));
  const best = ml.reduce((a, b) => (b.skill_vs_trend_pct > a.skill_vs_trend_pct ? b : a));
  const reliable = h12.p_vs_naive != null && h12.p_vs_naive < 0.05;
  const items = [
    { l: "12-month error vs. no change", v: sg(-h12.improvement_pct), s: `${h12.mape_trend}% vs ${h12.mape_naive}% average error`,
      p: <Pill tone={reliable ? "ok" : "warn"}>{reliable ? "Statistically reliable" : `Could be chance (p ${pv(h12.p_vs_naive)})`}</Pill> },
    { l: "Outcomes inside 80% range", v: `${h12.coverage80}%`, s: `${h12.n} forecasts, target 80%`,
      p: <Pill tone={h12.coverage80 >= 80 ? "ok" : "bad"}>{h12.coverage80 >= 80 ? "Range is honest" : "Range too narrow"}</Pill> },
    { l: "Direction called right", v: `${h12.direction}%`, s: `market rose in ${h12.base_up}% of the same windows`,
      p: <Pill tone="warn">No skill beyond the drift</Pill> },
    { l: "Best ML model vs. trend", v: sg(best.skill_vs_trend_pct), s: `${best.model}, 21-day forecasts`,
      p: <Pill tone={best.p_vs_trend != null && best.p_vs_trend < 0.05 && best.skill_vs_trend_pct > 0 ? "ok" : "warn"}>{best.skill_vs_trend_pct > 0 ? `Could be chance (p ${pv(best.p_vs_trend)})` : "Worse than the simple trend"}</Pill> },
  ];
  return (
    <div className="mb-4 grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3">
      {items.map((k) => (
        <div key={k.l} className="flex flex-col gap-1 rounded-2xl border border-[var(--bd)] bg-[var(--card)] px-4 py-3.5 shadow-[0_4px_18px_#0f172a14]">
          <small className="text-xs uppercase tracking-wide text-[var(--mut)]">{k.l}</small>
          <b className="text-[28px] tabular-nums tracking-tight">{k.v}</b>
          <span className="text-[13px] text-[var(--mut)]">{k.s}</span>
          {k.p}
        </div>
      ))}
    </div>
  );
}

export default function Evidence() {
  const [key, pick] = useHashKey(KEYS);
  const d = ALL[key];
  const hz = H.map((h) => d.horizons[h]);
  const misses = d.backtest12.filter((p) => !p.inside);
  const last = misses[misses.length - 1];
  const bestRow = d.ml.table.find((r) => r.model === d.ml.best)!;
  const reliablyBetter = d.ml.table.filter((r) => !["Trend", "No change"].includes(r.model) && r.p_vs_trend != null && r.p_vs_trend < 0.05 && r.skill_vs_trend_pct > 0).length;
  const mlCount = d.ml.table.length - 2;
  return (
    <>
      <header className="bg-[image:var(--hero)] px-4 pb-[70px] pt-7 text-white">
        <div className="mx-auto max-w-[1080px]">
          <PageNav active="/evidence" indexKey={key} />
          <div className="mb-3.5 inline-flex gap-0.5 rounded-[10px] bg-white/10 p-[3px]">
            {KEYS.map((k) => (
              <button key={k} onClick={() => pick(k)} className={`rounded-lg px-4 py-1.5 text-sm ${k === key ? "bg-white font-semibold text-slate-900" : "text-[#d6e4f0]"}`}>{ALL[k].name}</button>
            ))}
          </div>
          <h1 className="m-0 text-[26px] tracking-tight">Does the {d.name} forecast work?</h1>
          <p className="mt-1 max-w-[680px] text-[#b6c8d8]">
            Partly. It gives an honest range for where the index may be in 6 to 12 months. It does not predict short-term moves, and no machine-learning model we tried reliably beat it ({reliablyBetter} of {mlCount}).
          </p>
        </div>
      </header>

      <main key={key} className="mx-auto -mt-12 flex max-w-[1080px] flex-col gap-4 px-4 pb-12">
        <Kpis d={d} />

        <Card title="Every 12-month forecast, against what happened"
          desc={`Each forecast used only data available when it was made. ${misses.length} of ${d.backtest12.length} outcomes fell outside the 80% range (red).${last ? ` The latest, ${last.target}, missed by ${last.err_trend.toFixed(1)}% because the index ${last.pred > last.actual ? "fell while the forecast assumed growth" : "rose faster than the trend"}.` : ""}`}>
          <BacktestChart pts={d.backtest12} />
        </Card>

        <div className="grid gap-4 md:grid-cols-2">
          <Card title="Average error by horizon" desc="Lower is better. The trend forecast beats “assume no change” at every horizon.">
            <PairBars labels={H.map((h) => `${h} mo`)} a={{ name: "Trend forecast", v: hz.map((x) => x.mape_trend) }} b={{ name: "Assume no change", v: hz.map((x) => x.mape_naive) }} />
          </Card>
          <Card title="Direction hit rate vs. market up-rate" desc="The trend model always says “up”, so these bars match. High direction accuracy here is not skill.">
            <PairBars labels={H.map((h) => `${h} mo`)} a={{ name: "Direction correct", v: hz.map((x) => x.direction) }} b={{ name: "Market rose", v: hz.map((x) => x.base_up) }} max={100} fmt={(v) => Math.round(+v) + "%"} />
          </Card>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <Card title="Machine-learning challengers" desc={`Five models retrained every six months, tested on ${d.ml.test_days.toLocaleString("en-IN")} unseen trading days. Right of zero beats the trend.`}>
            <SkillChart rows={d.ml.table} />
          </Card>
          <Card title={`Best ML model (${d.ml.best}): predicted vs. actual`} desc={`With real skill, dots would follow the diagonal. Correlation ${bestRow.corr?.toFixed(2) ?? "—"}.`}>
            <PredActualScatter pts={d.ml.scatter} />
          </Card>
        </div>

        <Card title="Scorecard" desc="p-value: Diebold–Mariano test against “no change”, Newey–West errors for overlapping windows. Below 0.05 means unlikely to be luck.">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm tabular-nums">
              <thead><tr className="text-xs uppercase text-[var(--mut)]">
                {["Horizon", "Tested", "Trend error", "No-change error", "Error cut", "Trend closer", "In 80% range", "p-value"].map((h, i) => (
                  <th key={h} className={`whitespace-nowrap p-2 font-medium ${i ? "text-right" : "text-left"}`}>{h}</th>))}
              </tr></thead>
              <tbody>{H.map((h) => { const x = d.horizons[h]; return (
                <tr key={h} className="border-t border-[var(--bd)]">
                  <td className="p-2">{h} month{h === "1" ? "" : "s"}</td><td className="p-2 text-right">{x.n}</td>
                  <td className="p-2 text-right">{x.mape_trend.toFixed(2)}%</td><td className="p-2 text-right">{x.mape_naive.toFixed(2)}%</td>
                  <td className="p-2 text-right">{x.improvement_pct.toFixed(1)}%</td><td className="p-2 text-right">{x.win_rate}%</td>
                  <td className="p-2 text-right">{x.coverage80}%</td><td className="p-2 text-right">{pv(x.p_vs_naive)}</td>
                </tr>); })}</tbody>
            </table>
          </div>
        </Card>

        <Card title="How this was tested">
          <ul className="m-0 grid list-none gap-3 p-0 text-[13.5px] sm:grid-cols-2">
            <li><b>No look-ahead.</b> <span className="text-[var(--mut)]">Every forecast uses only data that existed on the day it was made. ML training sets are purged so no target overlaps the test window.</span></li>
            <li><b>Fair rivals.</b> <span className="text-[var(--mut)]">Each model is scored against “no change” and the simple trend, and only earns its place by beating them.</span></li>
            <li><b>Luck check.</b> <span className="text-[var(--mut)]">Diebold–Mariano tests with Newey–West errors, which correct for overlapping forecast windows.</span></li>
            <li><b>Data.</b> <span className="text-[var(--mut)]">{d.source}, {d.daily_rows.toLocaleString("en-IN")} daily closes from {d.first} to {d.asof}. Latest level {f0(d.current)}.</span></li>
          </ul>
        </Card>
      </main>
      <footer className="px-4 pb-8 pt-2 text-center text-[12.5px] text-[var(--mut)]">Statistical exercise, not investment advice. Reproduce with <code>python stakeholder_eval.py</code>.</footer>
    </>
  );
}
