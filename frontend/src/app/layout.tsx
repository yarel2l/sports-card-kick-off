import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/Providers";
import SiteHeader from "@/components/SiteHeader";

export const metadata: Metadata = {
  title: {
    default: "Sports Card Kickoff — Card prices, comps & market data",
    template: "%s · Sports Card Kickoff",
  },
  description:
    "Search sports card prices and sold comps aggregated from eBay, 130Point, COMC and Goldin. Real market value, price history and population data for collectors and investors.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col bg-slate-50 text-slate-900">
        <Providers>
          <SiteHeader />
          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
          <footer className="border-t border-slate-200 py-8 text-center text-xs text-slate-400">
            Aggregated market data for informational purposes only.
          </footer>
        </Providers>
      </body>
    </html>
  );
}
