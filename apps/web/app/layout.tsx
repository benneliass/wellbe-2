import "@wellbe/ui/tokens.css";
import "./globals.css";
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import localFont from "next/font/local";
import { Providers } from "./providers";

// Self-hosted (latin subset, variable weight) so `next build` never reaches out to
// Google Fonts — image builds must work offline. See app/fonts/README.md.
const figtree = localFont({
  src: [{ path: "./fonts/figtree-latin-wght-normal.woff2", weight: "300 900", style: "normal" }],
  variable: "--font-figtree",
  display: "swap",
  fallback: ["system-ui", "sans-serif"],
});

const notoSans = localFont({
  src: [{ path: "./fonts/noto-sans-latin-wght-normal.woff2", weight: "100 900", style: "normal" }],
  variable: "--font-noto-sans",
  display: "swap",
  fallback: ["system-ui", "sans-serif"],
});

const jetbrains = localFont({
  src: [
    { path: "./fonts/jetbrains-mono-latin-wght-normal.woff2", weight: "100 800", style: "normal" },
  ],
  variable: "--font-jetbrains",
  display: "swap",
  fallback: ["ui-monospace", "monospace"],
  adjustFontFallback: false,
});

export const metadata: Metadata = {
  title: "WellBe",
  description: "Your personal health continuity workspace.",
};

// viewport-fit=cover exposes env(safe-area-inset-*) to the fixed mobile bottom nav.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // suppressHydrationWarning tolerates attributes injected into <html>/<body>
    // by browser extensions before React hydrates. Without it, React 19 surfaces
    // such third-party DOM mutations as a "removeChild of null" crash. This only
    // applies one level deep, so genuine app-level mismatches are still reported.
    <html
      lang="en"
      className={`${figtree.variable} ${notoSans.variable} ${jetbrains.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Runtime auth config (app/auth-config.js/route.ts). Deliberately
            synchronous: it must set window.__WELLBE_AUTH_CONFIG__ before hydration. */}
        {/* eslint-disable-next-line @next/next/no-sync-scripts */}
        <script src="/auth-config.js" />
      </head>
      <body suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
