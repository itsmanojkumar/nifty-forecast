import type { Metadata } from "next";
import Dashboard from "@/components/Dashboard";

export const metadata: Metadata = { title: "Forecast · Nifty Forecasts" };

export default function ForecastPage() {
  return <Dashboard />;
}
