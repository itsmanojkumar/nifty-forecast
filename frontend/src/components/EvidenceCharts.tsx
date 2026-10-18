"use client";
import { Bar, Line, Scatter } from "react-chartjs-2";
import { useTheme } from "./Charts";
import { BacktestPoint, MlRow, f0, mon } from "@/lib/types";

const pct = (v: number | string) => (+v).toFixed(1) + "%";

/** every 12-month forecast vs. the outcome, with its 80% range; misses in red */
export function BacktestChart({ pts }: { pts: BacktestPoint[] }) {
  const t = useTheme();
  const data = {
    labels: pts.map((p) => p.target),
    datasets: [
      { label: "hi", data: pts.map((p) => p.hi), borderWidth: 0, pointRadius: 0, fill: "+1", backgroundColor: t.acc + "26" },
      { label: "lo", data: pts.map((p) => p.lo), borderWidth: 0, pointRadius: 0 },
      { label: "Forecast made 12 months earlier", data: pts.map((p) => p.pred), borderColor: t.acc, borderWidth: 2.2, pointRadius: 0 },
      {
        label: "Actual", data: pts.map((p) => p.actual), borderColor: t.tx + "80", borderWidth: 1.4,
        pointRadius: pts.map((p) => (p.inside ? 2.5 : 5)), pointBackgroundColor: pts.map((p) => (p.inside ? t.tx : t.dn)), pointBorderWidth: 0,
      },
    ],
  };
  const options = {
    maintainAspectRatio: false, interaction: { mode: "index" as const, intersect: false },
    plugins: {
      legend: { labels: { color: t.tx, filter: (i: { text: string }) => i.text !== "hi" && i.text !== "lo" } },
      tooltip: {
        filter: (i: { dataset: { label?: string } }) => i.dataset.label !== "hi" && i.dataset.label !== "lo",
        callbacks: {
          title: (it: { dataIndex: number }[]) => `${mon(pts[it[0].dataIndex].target)} (made ${mon(pts[it[0].dataIndex].origin)})`,
          label: (i: { dataset: { label?: string }; parsed: { y: number } }) => ` ${i.dataset.label}: ${f0(i.parsed.y)}`,
          afterBody: (it: { dataIndex: number }[]) => {
            const p = pts[it[0].dataIndex];
            return [`80% range: ${f0(p.lo)} – ${f0(p.hi)}`, `Error: ${pct(p.err_trend)}${p.inside ? "" : "  · outside range"}`];
          },
        },
      },
    },
    scales: {
      x: { ticks: { color: t.tx, maxTicksLimit: 8, callback(this: { getLabelForValue(v: number): string }, v: number | string) { return mon(this.getLabelForValue(+v)); } }, grid: { display: false } },
      y: { ticks: { color: t.tx, callback: (v: number | string) => f0(+v) }, grid: { color: t.bd } },
    },
  };
  return <div className="relative h-[340px]"><Line data={data} options={options as never} /></div>;
}

/** two series per horizon (e.g. trend vs no-change error) */
export function PairBars({ labels, a, b, max, fmt = pct }: { labels: string[]; a: { name: string; v: number[] }; b: { name: string; v: number[] }; max?: number; fmt?: (v: number | string) => string }) {
  const t = useTheme();
  const data = {
    labels,
    datasets: [
      { label: a.name, data: a.v, backgroundColor: t.acc, borderRadius: 5, maxBarThickness: 30 },
      { label: b.name, data: b.v, backgroundColor: t.bd, borderRadius: 5, maxBarThickness: 30 },
    ],
  };
  const options = {
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: t.tx } }, tooltip: { callbacks: { label: (i: { dataset: { label?: string }; parsed: { y: number } }) => ` ${i.dataset.label}: ${fmt(i.parsed.y)}` } } },
    scales: { x: { ticks: { color: t.tx }, grid: { display: false } }, y: { min: 0, max, ticks: { color: t.tx, callback: fmt }, grid: { color: t.bd } } },
  };
  return <div className="relative h-[260px]"><Bar data={data} options={options as never} /></div>;
}

/** ML skill vs the trend baseline; right of zero = better */
export function SkillChart({ rows }: { rows: MlRow[] }) {
  const t = useTheme();
  const r = rows.filter((x) => x.model !== "Trend");
  const data = {
    labels: r.map((x) => x.model),
    datasets: [{ data: r.map((x) => x.skill_vs_trend_pct), backgroundColor: r.map((x) => (x.skill_vs_trend_pct > 0 ? t.acc : t.dn + "b3")), borderRadius: 5, maxBarThickness: 26 }],
  };
  const options = {
    indexAxis: "y" as const, maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (i: { dataIndex: number }) => {
            const x = r[i.dataIndex], p = x.p_vs_trend;
            return [` Skill vs trend: ${x.skill_vs_trend_pct > 0 ? "+" : ""}${x.skill_vs_trend_pct}%`, p == null ? "" : ` p-value ${p.toFixed(3)} · ${p < 0.05 ? (x.skill_vs_trend_pct > 0 ? "reliably better" : "reliably worse") : "could be chance"}`,
              x.direction == null ? "" : ` Direction right: ${x.direction}%`].filter(Boolean);
          },
        },
      },
    },
    scales: {
      x: { ticks: { color: t.tx, callback: (v: number | string) => (+v > 0 ? "+" : "") + v + "%" }, grid: { color: (c: { tick: { value: number } }) => (c.tick.value === 0 ? t.tx : t.bd) } },
      y: { ticks: { color: t.tx }, grid: { display: false } },
    },
  };
  return <div className="relative h-[260px]"><Bar data={data} options={options as never} /></div>;
}

/** predicted vs actual 21-day return of the best ML model */
export function PredActualScatter({ pts }: { pts: [number, number][] }) {
  const t = useTheme();
  const m = Math.ceil(Math.max(...pts.map((p) => Math.abs(p[1]))));
  const xm = Math.max(2, Math.ceil(Math.max(...pts.map((p) => Math.abs(p[0]))) * 1.2));
  const data = {
    datasets: [
      { label: "One test day", data: pts.map(([x, y]) => ({ x, y })), backgroundColor: t.acc + "73", pointRadius: 2.6, pointHoverRadius: 5 },
      { label: "Perfect prediction", data: [{ x: -m, y: -m }, { x: m, y: m }], showLine: true, borderColor: t.tx, borderDash: [5, 5], borderWidth: 1, pointRadius: 0 },
    ],
  };
  const options = {
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: t.tx } }, tooltip: { callbacks: { label: (i: { parsed: { x: number; y: number } }) => ` predicted ${i.parsed.x.toFixed(2)}%, actual ${i.parsed.y.toFixed(2)}%` } } },
    scales: {
      x: { min: -xm, max: xm, title: { display: true, text: "Predicted 21-day return", color: t.tx }, ticks: { color: t.tx, callback: (v: number | string) => v + "%" }, grid: { color: t.bd } },
      y: { min: -m, max: m, title: { display: true, text: "Actual 21-day return", color: t.tx }, ticks: { color: t.tx, callback: (v: number | string) => v + "%" }, grid: { color: t.bd } },
    },
  };
  return <div className="relative h-[300px]"><Scatter data={data} options={options as never} /></div>;
}
