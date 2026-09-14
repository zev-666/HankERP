import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/erp/QueryProvider";

export const metadata: Metadata = {
  title: "龜山壓克力 | 智慧工廠ERP",
  description: "桃園龜山複合式壓克力展示架製造商 — 智慧製造ERP系統",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-TW">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
