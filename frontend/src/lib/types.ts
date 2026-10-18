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
}

export type AllData = Record<string, IndexData>;

export const f0 = (v: number) => Math.round(v).toLocaleString("en-IN");
export const pc = (v: number) => (v > 0 ? "+" : "") + v.toFixed(1) + "%";
export const mon = (s: string) => {
  const [y, m] = s.split("-");
  return new Date(+y, +m - 1).toLocaleString("en", { month: "short", year: "numeric" });
};
