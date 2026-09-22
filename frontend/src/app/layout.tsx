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
      <head>
        {/* 官網字體：Noto Sans TC（中文）＋ IBM Plex Mono（規格與數字）。
            用 <link> 在瀏覽器端載入，不走 next/font —— 避免建置期需要連網（見 v1.0 bug#9） */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        {/* 此規則是 Pages Router 時代針對 _document.js 的檢查；App Router 的根 layout
            本來就套用到每一頁，不存在「只載入單一頁」的問題，故停用 */}
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
        />
      </head>
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
