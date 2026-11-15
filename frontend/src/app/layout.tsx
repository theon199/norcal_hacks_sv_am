import type { Metadata } from "next";
import { Geist_Mono, Schibsted_Grotesk, STIX_Two_Text } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const ui = Schibsted_Grotesk({
  variable: "--font-ui",
  subsets: ["latin"],
});

// Used only for claims: the typeface of a published paper, next to the instrument's sans.
const claim = STIX_Two_Text({
  variable: "--font-claim",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LabMirror",
  description: "Don't just trust the research. Test it. An independent stress test for machine-learning claims.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${ui.variable} ${claim.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <header className="border-b border-line">
          <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-3">
            <Link href="/" className="flex items-center gap-2 text-base font-bold tracking-tight">
              {/* A disc and its reflection: the claim on one side, the measurement on the other. */}
              <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
                <path d="M9 2a8 8 0 0 0 0 16z" fill="var(--accent)" />
                <path d="M11 2.75a7.25 7.25 0 0 1 0 14.5z" fill="none" stroke="var(--accent)" strokeWidth="1.5" />
              </svg>
              LabMirror
            </Link>
            <p className="hidden text-right text-xs text-muted sm:block">Stress tests for machine-learning claims</p>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
