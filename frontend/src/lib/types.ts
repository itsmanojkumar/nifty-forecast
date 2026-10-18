export type Band = [string, number, number, number]; // [label, forecast, low(p10), high(p90)]

export interface IndexData {
  name: string;
  tag: string;
  modelNote: string;
  note1: string;
  note2: string;
  asof: string;
  current: number;
  hist: [string, number][];
  fc: Band[];
  short: { hist: [string, number][]; fc: Band[] };
  check: { mape_pct: number; end_err_pct: number; inside_band_pct: number; pred: number[]; actual: number[]; months: string[] };
  acc: { h: string; err: number; dir: number }[];
  models: [string, number][];
  short_meta?: {
    made_for: string; last_close_date: string; last_close: number; day1_return_pct: number; drift_pct_per_day: number;
    india_vix: number; overnight_pct: { spx: number; ndx: number; es: number }; model: string;
  };
}

export type AllData = Record<string, IndexData>;

export const f0 = (v: number) => Math.round(v).toLocaleString("en-IN");
export const pc = (v: number) => (v > 0 ? "+" : "") + v.toFixed(1) + "%";
export const mon = (s: string) => {
  const [y, m] = s.split("-");
  return new Date(+y, +m - 1).toLocaleString("en", { month: "short", year: "numeric" });
};

// ---- model evidence (written by stakeholder_eval.py -> export_evidence.py) ----
export interface HorizonStats {
  n: number; mape_trend: number; mape_naive: number; improvement_pct: number; win_rate: number;
  direction: number; base_up: number; coverage80: number; p_vs_naive: number | null;
}
export interface BacktestPoint { origin: string; target: string; pred: number; lo: number; hi: number; actual: number; inside: boolean; err_trend: number }
export interface MlRow { model: string; rmse_pct: number; skill_vs_trend_pct: number; direction: number | null; corr: number | null; p_vs_trend: number | null }
export interface Evidence {
  name: string; source: string; first: string; daily_rows: number; months: number; asof: string; current: number;
  dec2027: [number, number, number];
  horizons: Record<"1" | "3" | "6" | "12", HorizonStats>;
  backtest12: BacktestPoint[];
  ml: { test_days: number; first: string; last: string; up_share: number; table: MlRow[]; best: string; scatter: [number, number][] };
}
export type AllEvidence = Record<string, Evidence>;
