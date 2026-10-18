import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nifty Forecasts",
  description: "Forecasts for Nifty Metal and Nifty 50 to Dec 2027, with accuracy checks. Statistical exercise, not investment advice.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
