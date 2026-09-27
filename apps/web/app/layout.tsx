import "@wellbe/ui/tokens.css";
import "./globals.css";
import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Figtree, JetBrains_Mono, Noto_Sans } from "next/font/google";
import { Providers } from "./providers";

const figtree = Figtree({
  subsets: ["latin"],
  variable: "--font-figtree",
  display: "swap",
  weight: ["500", "600", "700", "800"],
});

const notoSans = Noto_Sans({
  subsets: ["latin"],
  variable: "--font-noto-sans",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains",
  display: "swap",
  weight: ["400", "500"],
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
