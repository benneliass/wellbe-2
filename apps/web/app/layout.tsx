import "@wellbe/ui/tokens.css";
import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { JetBrains_Mono, Newsreader, Plus_Jakarta_Sans } from "next/font/google";
import { Providers } from "./providers";

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta",
  display: "swap",
  weight: ["300", "400", "500", "600", "700", "800"],
});

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-newsreader",
  display: "swap",
  weight: ["400"],
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

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // suppressHydrationWarning tolerates attributes injected into <html>/<body>
    // by browser extensions before React hydrates. Without it, React 19 surfaces
    // such third-party DOM mutations as a "removeChild of null" crash. This only
    // applies one level deep, so genuine app-level mismatches are still reported.
    <html
      lang="en"
      className={`${jakarta.variable} ${jetbrains.variable} ${newsreader.variable}`}
      suppressHydrationWarning
    >
      <body suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
