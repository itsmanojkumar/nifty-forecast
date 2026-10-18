import Link from "next/link";

const PAGES = [
  { href: "/", label: "Overview" },
  { href: "/forecast", label: "Forecast" },
  { href: "/evidence", label: "Evidence" },
];

/** top-level page switch; keeps the selected index (#metal / #nifty50) across pages */
export default function PageNav({ active, indexKey }: { active: string; indexKey?: string }) {
  const hash = indexKey ? `#${indexKey}` : "";
  return (
    <nav aria-label="Pages" className="mb-6 flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-b border-white/15 pb-3 text-sm">
      <Link href="/" className="font-semibold tracking-tight text-white">Nifty Forecasts</Link>
      <div className="flex gap-5">
        {PAGES.map((p) => (
          <Link key={p.href} href={p.href + hash} aria-current={p.href === active ? "page" : undefined}
            className={`border-b-2 pb-0.5 transition-colors ${p.href === active ? "border-[var(--acc2)] text-white" : "border-transparent text-[#b6c8d8] hover:text-white"}`}>
            {p.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
