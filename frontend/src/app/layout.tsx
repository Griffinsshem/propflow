import type { Metadata } from "next";
import { connection } from "next/server";
import type { ReactNode } from "react";

import { Providers } from "@/components/providers";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "PropFlow", template: "%s · PropFlow" },
  description: "Property operations: maintenance, work orders and tenants in one place.",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  // Render per request so every page carries the CSP nonce issued in src/proxy.ts.
  await connection();
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
