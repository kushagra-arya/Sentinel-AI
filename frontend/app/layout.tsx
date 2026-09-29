import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { Providers } from "@/app/providers";
import "@/styles/globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "SentinelAI",
  description: "Industrial safety intelligence infrastructure shell"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} min-h-screen bg-background font-sans text-foreground`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
