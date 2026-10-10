import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RiskPulse AI | Foundation",
  description: "RiskPulse AI service status and foundation environment.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

