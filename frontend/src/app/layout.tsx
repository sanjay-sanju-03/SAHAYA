import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "SAHAYA — Inclusive Emergency Decision Engine",
  description:
    "AI-powered emergency decision support. Before we send help, let's make sure it can actually help. AI understands. Rules verify. Humans decide.",
  keywords: ["emergency", "accessibility", "disaster management", "inclusive", "Kerala"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <nav className="nav" role="banner">
          <Link href="/" className="nav-logo leading-tight" aria-label="SAHAYA home">
            <span className="block text-2xl" style={{ color: "#2dd4bf" }}>SAHAYA</span>
            <span className="text-xs font-medium" style={{ color: "rgba(255,255,255,0.58)" }}>Inclusive Emergency Decision Engine</span>
          </Link>
          <span className="nav-eyebrow hidden sm:block">● DECISION SUPPORT</span>
        </nav>
        <main id="main-content">{children}</main>
      </body>
    </html>
  );
}
