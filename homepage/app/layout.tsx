import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
  preload: true,
});

export const metadata: Metadata = {
  title: "CORES — Cognitive Runtime for Embodied Systems",
  description: "A deterministic, modular runtime for autonomous robotics. Research-grade scheduling that ships on real robots.",
  keywords: ["robotics", "runtime", "scheduling", "autonomous systems", "real-time", "lexicographic optimization"],
  authors: [{ name: "CORES Team" }],
  openGraph: {
    title: "CORES — Cognitive Runtime for Embodied Systems",
    description: "A deterministic, modular runtime for autonomous robotics.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#0B0D12",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} font-sans`}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="min-h-screen bg-paper text-ink">
        {children}
      </body>
    </html>
  );
}