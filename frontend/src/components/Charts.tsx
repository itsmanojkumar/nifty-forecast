"use client";
import { useEffect, useState } from "react";
import { Line, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler, Tooltip, Legend,
} from "chart.js";
import { Band, IndexData, f0, mon } from "@/lib/types";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler, Tooltip, Legend);

type Theme = { tx: string; bd: string; acc: string };
const read = (): Theme => {
  const s = getComputedStyle(document.documentElement);
  const g = (n: string) => s.getPropertyValue(n).trim();
  return { tx: g("--mut"), bd: g("--bd"), acc: g("--acc") };
};
function useTheme(): Theme {
  const [t, setT] = useState<Theme>({ tx: "#64748b", bd: "#e2e8f0", acc: "#0e7490" });
  useEffect(() => {
    const apply = () => setT(read());
    apply();
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);
  return t;
}

const hide = (i: { text: string }) => i.text !== "hi" && i.text !== "lo";
const scales = (t: Theme, tick?: (v: number | string) => string, maxTicks = 9) => ({
  x: { ticks: { color: t.tx, maxTicksLimit: maxTicks }, grid: { display: false } },
  y: { ticks: { color: t.tx, callback: (v: number | string) => (tick ? tick(v) : f0(+v)) }, grid: { color: t.bd } },
});

/** history + forecast with 80% band */
export function BandChart({ hist, fc, label, height = 360, dots = false }: { hist: [string, number][]; fc: Band[]; label: (s: string) => string; height?: number; dots?: boolean }) {
  const t = useTheme();
  const n = hist.length, last = hist[n - 1][1], pad = Array(n - 1).fill(null);
  const labels = [...hist.map((x) => x[0]), ...fc.map((x) => x[0])];
  const data = {
    labels,
    datasets: [
      { label: "Actual", data: [...hist.map((x) => x[1]), ...Array(fc.length).fill(null)], borderColor: t.tx, borderWidth: 1.8, pointRadius: dots ? 2 : 0, tension: 0.15 },
      { label: "hi", data: [...pad, last, ...fc.map((x) => x[3])], borderWidth: 0, pointRadius: 0, fill: "+1", backgroundColor: t.acc + "2e" },
      { label: "lo", data: [...pad, last, ...fc.map((x) => x[2])], borderWidth: 0, pointRadius: 0 },
      { label: "Forecast", data: [...pad, last, ...fc.map((x) => x[1])], borderColor: t.acc, borderWidth: 2.6, pointRadius: dots ? 2 : 0 },
    ],
  };
  const options = {
    maintainAspectRatio: false, interaction: { mode: "index" as const, intersect: false },
    plugins: { legend: { labels: { color: t.tx, filter: hide } }, tooltip: { filter: (i: { dataset: { label?: string } }) => i.dataset.label !== "hi" && i.dataset.label !== "lo" } },
    scales: { ...scales(t, undefined, dots ? 10 : 9), x: { ticks: { color: t.tx, maxTicksLimit: dots ? 10 : 9, callback(this: { getLabelForValue(v: number): string }, v: number | string) { return label(this.getLabelForValue(+v)); } }, grid: { display: false } } },
  };
  return <div style={{ height }} className="relative"><Line data={data} options={options as never} /></div>;
}

export function ModelsChart({ models }: { models: IndexData["models"] }) {
  const t = useTheme();
  const data = { labels: models.map((m) => m[0]), datasets: [{ data: models.map((m) => m[1]), backgroundColor: models.map((m) => (m[0].includes("winner") ? t.acc : t.bd)), borderRadius: 6 }] };
  const options = {
    indexAxis: "y" as const, maintainAspectRatio: false, plugins: { legend: { display: false } },
    scales: { x: { ticks: { color: t.tx, callback: (v: number | string) => v + "%" }, grid: { color: t.bd } }, y: { ticks: { color: t.tx }, grid: { display: false } } },
  };
  return <div className="relative h-[250px]"><Bar data={data} options={options as never} /></div>;
}

export function CheckChart({ check }: { check: IndexData["check"] }) {
  const t = useTheme();
  const data = {
    labels: check.months.map(mon),
    datasets: [
      { label: "Actual", data: check.actual, borderColor: t.tx, borderWidth: 2, pointRadius: 2 },
      { label: "Forecast made 12 months ago", data: check.pred, borderColor: t.acc, borderDash: [6, 4], borderWidth: 2, pointRadius: 0 },
    ],
  };
  const options = { maintainAspectRatio: false, plugins: { legend: { labels: { color: t.tx } } }, scales: scales(t, undefined, 12) };
  return <div className="relative h-[260px]"><Line data={data} options={options as never} /></div>;
}
