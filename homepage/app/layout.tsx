import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
  preload: true,
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: "400",
  display: "swap",
  variable: "--font-display",
  preload: true,
});

export const metadata: Metadata = {
  title: "CORES: Cognitive Runtime for Embodied Systems",
  description: "A robot has one battery, one CPU, and one chance to get home. CORES decides which cognitive modules run, in what order, and under what constraints.",
  keywords: ["robotics", "runtime", "scheduling", "autonomous systems", "real-time", "lexicographic optimization"],
  authors: [{ name: "CORES Team" }],
  openGraph: {
    title: "CORES — Cognitive Runtime for Embodied Systems",
    description: "A deterministic, modular runtime for autonomous robotics.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable}`}>
      <body className="min-h-screen bg-canvas-white text-graphite font-sans">
        {children}
      </body>
    </html>
  );
}
