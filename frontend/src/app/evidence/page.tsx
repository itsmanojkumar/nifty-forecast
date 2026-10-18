import type { Metadata } from "next";
import Evidence from "@/components/Evidence";

export const metadata: Metadata = { title: "Evidence · Nifty Forecasts", description: "Walk-forward backtests: does the Nifty forecast beat simple rivals, and is its range honest?" };

export default function EvidencePage() {
  return <Evidence />;
}
