"use client";
import Link from "next/link";
import data from "@/data/indices.json";
import ev from "@/data/evidence.json";
import { AllData, AllEvidence, f0, pc } from "@/lib/types";
import { BandChart } from "./Charts";
import PageNav from "./PageNav";

const ALL = data as unknown as AllData;
const EV = ev as unknown as AllEvidence;
const KEYS = Object.keys(ALL);

const STEPS = [
  { t: "Collect", d: "Official NSE daily closes for Nifty Metal and Yahoo Finance history for Nifty 50, cleaned and checked for gaps and outliers." },
  { t: "Engineer features", d: "Momentum over 1 day to 1 year, volatility, drawdown from the 52-week high and distance from the 100-day average." },
  { t: "Train challengers", d: "Trend, ARIMA, exponential smoothing, Ridge, random forest, tuned gradient boosting, a GRU neural net and an ensemble." },
  { t: "Test without look-ahead", d: "Walk-forward backtests that retrain on past data only, scored against simple rivals with a statistical luck check." },
  { t: "Publish", d: "Python writes JSON for this static Next.js site, so every number here comes straight from the last model run." },
];
const STACK = ["Python", "pandas", "scikit-learn", "PyTorch", "statsmodels", "SciPy", "Next.js", "TypeScript", "Chart.js", "Tailwind CSS"];

function IndexCard({ k }: { k: string }) {
  const d = ALL[k], e = EV[k], fin = d.fc[d.fc.length - 1], chg = (fin[1] / d.current - 1) * 100;
  const hist = d.hist.slice(-36);
  return (
    <article className="flex min-w-0 flex-col gap-3 rounded-2xl border border-[var(--bd)] bg-[var(--card)] p-5 shadow-[0_8px_30px_#0f172a1a]">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="m-0 text-xl font-semibold tracking-tight">{d.name}</h2>
        <span className="text-xs text-[var(--mut)]">as of {d.asof}</span>
      </div>
      <dl className="m-0 grid grid-cols-3 gap-3 text-sm">
        <div><dt className="text-xs text-[var(--mut)]">Today</dt><dd className="m-0 text-lg font-semibold tabular-nums">{f0(d.current)}</dd></div>
        <div><dt className="text-xs text-[var(--mut)]">Dec 2027</dt><dd className={`m-0 text-lg font-semibold tabular-nums ${chg >= 0 ? "text-[var(--up)]" : "text-[var(--dn)]"}`}>{f0(fin[1])}</dd><span className="text-xs text-[var(--mut)]">{pc(chg)}</span></div>
        <div><dt className="text-xs text-[var(--mut)]">80% range</dt><dd className="m-0 text-sm font-semibold tabular-nums">{f0(fin[2])} – {f0(fin[3])}</dd></div>
      </dl>
      <BandChart hist={hist} fc={d.fc} label={(s) => s.slice(0, 4)} height={190} />
      <p className="m-0 text-[13px] text-[var(--mut)]">
        Backtest: 12-month error {e.horizons["12"].mape_trend}% vs {e.horizons["12"].mape_naive}% for “no change”; {e.horizons["12"].coverage80}% of outcomes inside the range.
      </p>
      <div className="mt-auto flex flex-wrap gap-4 text-sm font-medium">
        <Link href={`/forecast#${k}`} className="text-[var(--acc)] hover:underline">Open forecast →</Link>
        <Link href={`/evidence#${k}`} className="text-[var(--acc)] hover:underline">See the evidence →</Link>
      </div>
    </article>
  );
}

export default function Landing() {
  const m = EV.metal, n = EV.nifty50;
  const mlBetter = [m, n].map((e) => e.ml.table.filter((r) => !["Trend", "No change"].includes(r.model) && r.p_vs_trend != null && r.p_vs_trend < 0.05 && r.skill_vs_trend_pct > 0).length);
  const mlTotal = m.ml.table.length - 2;
  const findings = [
    { tone: "text-[var(--up)]", label: "Works", t: "An honest range",
      d: `Its 80% range held for ${m.horizons["12"].coverage80}% (Nifty Metal) and ${n.horizons["12"].coverage80}% (Nifty 50) of 12-month outcomes, slightly wider than needed.` },
    { tone: "text-[var(--acc2)]", label: "Modest", t: "A small edge over “no change”",
      d: `12-month error is ${m.horizons["12"].improvement_pct}% and ${n.horizons["12"].improvement_pct}% lower than assuming the index stays put, but the gap could still be chance.` },
    { tone: "text-[var(--dn)]", label: "Doesn’t work", t: "No market timing",
      d: `Direction accuracy only matches how often the market rose. ${mlBetter[0] + mlBetter[1]} of ${mlTotal * 2} machine-learning tests reliably beat the simple trend.` },
  ];
  return (
    <>
      <header className="bg-[image:var(--hero)] px-4 pb-[120px] pt-7 text-white">
        <div className="mx-auto max-w-[1080px]">
          <PageNav active="/" />
          <span className="mb-3 inline-block rounded-full border border-white/35 px-2.5 py-0.5 text-xs text-[#d6e4f0]">Machine-learning project · Nifty Metal &amp; Nifty 50</span>
          <h1 className="m-0 max-w-[760px] text-[clamp(28px,4.6vw,46px)] font-semibold leading-[1.1] tracking-tight [text-wrap:balance]">
            Where Indian markets may be by Dec 2027, and how far to trust it.
          </h1>
          <p className="mb-6 mt-4 max-w-[620px] text-[17px] leading-relaxed text-[#b6c8d8]">
            Index forecasts built from {f0(m.daily_rows + n.daily_rows)} daily closes, tested against every forecast they could have made in the past, with the misses shown openly.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/forecast" className="rounded-xl bg-white px-5 py-2.5 text-sm font-semibold text-slate-900 hover:bg-[#e6edf5]">See the forecast</Link>
            <Link href="/evidence" className="rounded-xl border border-white/40 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/10">Read the evidence</Link>
          </div>
        </div>
      </header>

      <main className="mx-auto -mt-[84px] flex max-w-[1080px] flex-col gap-12 px-4 pb-14">
        <section aria-label="Indices" className="grid gap-4 md:grid-cols-2">
          {KEYS.map((k) => <IndexCard key={k} k={k} />)}
        </section>

        <section aria-labelledby="found" className="flex flex-col gap-4">
          <div>
            <h2 id="found" className="m-0 text-2xl font-semibold tracking-tight">What the evidence says</h2>
            <p className="m-0 mt-1 text-[var(--mut)]">Five years of walk-forward backtests on both indices.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {findings.map((f) => (
              <div key={f.t} className="flex flex-col gap-1.5 rounded-2xl border border-[var(--bd)] bg-[var(--card)] p-5">
                <span className={`inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide ${f.tone}`}><i className="h-2 w-2 rounded-full bg-current" />{f.label}</span>
                <h3 className="m-0 text-lg font-semibold">{f.t}</h3>
                <p className="m-0 text-sm text-[var(--mut)]">{f.d}</p>
              </div>
            ))}
          </div>
          <Link href="/evidence" className="self-start text-sm font-medium text-[var(--acc)] hover:underline">Full evidence report →</Link>
        </section>

        <section aria-labelledby="how" className="flex flex-col gap-4">
          <h2 id="how" className="m-0 text-2xl font-semibold tracking-tight">How it’s built</h2>
          <ol className="m-0 grid list-none gap-3 p-0 sm:grid-cols-2 lg:grid-cols-5">
            {STEPS.map((s, i) => (
              <li key={s.t} className="flex flex-col gap-1.5 rounded-2xl border border-[var(--bd)] bg-[var(--card)] p-4">
                <span className="text-xs font-semibold tabular-nums text-[var(--acc)]">Step {i + 1}</span>
                <b className="text-[15px]">{s.t}</b>
                <span className="text-[13px] text-[var(--mut)]">{s.d}</span>
              </li>
            ))}
          </ol>
          <div className="flex flex-wrap gap-2">
            {STACK.map((s) => <span key={s} className="rounded-full border border-[var(--bd)] bg-[var(--card)] px-3 py-1 text-xs text-[var(--mut)]">{s}</span>)}
          </div>
        </section>
      </main>

      <footer className="border-t border-[var(--bd)] px-4 py-6 text-center text-[12.5px] text-[var(--mut)]">
        Statistical exercise, not investment advice. Code and data:{" "}
        <a className="text-[var(--acc)]" href="https://github.com/itsmanojkumar/nifty-forecast">github.com/itsmanojkumar/nifty-forecast</a>
      </footer>
    </>
  );
}
