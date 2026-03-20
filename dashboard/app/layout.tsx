import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "@/app/globals.css";
import { Providers } from "@/components/providers";
import { env } from "@/lib/env";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: env.appName,
  description: "Production-ready dashboard for monitoring and controlling your Discord bot.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
