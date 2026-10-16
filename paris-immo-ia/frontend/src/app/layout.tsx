import type { Metadata } from "next";
import Link from "next/link";
import { Fraunces, Inter } from "next/font/google";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces" });

export const metadata: Metadata = {
  title: "Paris Immo IA",
  description: "Trouvez l'appartement parisien fait pour vous, en une conversation.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${inter.variable} ${fraunces.variable}`}>
      <body className="min-h-dvh font-sans">
        <header className="sticky top-0 z-20 border-b bg-background/85 backdrop-blur">
          <nav className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
            <Link href="/" className="whitespace-nowrap font-serif text-lg font-semibold tracking-tight">
              Paris<span className="text-ai-foreground">·</span>Immo IA
            </Link>
            <div className="flex items-center gap-1 whitespace-nowrap text-sm">
              <Link href="/search" className="rounded-md px-2 py-1.5 hover:bg-accent sm:px-3">
                Je cherche
              </Link>
              <Link href="/proprietaire" className="rounded-md px-2 py-1.5 hover:bg-accent sm:px-3">
                <span className="sm:hidden">Propriétaire</span>
                <span className="hidden sm:inline">Je loue mon bien</span>
              </Link>
            </div>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
