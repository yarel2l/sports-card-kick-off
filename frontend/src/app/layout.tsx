import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

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
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-slate-900 text-sm text-white">
                SC
              </span>
              <span>Sports Card Kickoff</span>
            </Link>
            <nav className="text-sm text-slate-500">
              <Link href="/search" className="hover:text-slate-900">
                Browse
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">{children}</main>
        <footer className="border-t border-slate-200 py-8 text-center text-xs text-slate-400">
          Aggregated market data for informational purposes only.
        </footer>
      </body>
    </html>
  );
}
