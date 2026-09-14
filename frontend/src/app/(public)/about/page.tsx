import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site/SiteHeader";

export const metadata: Metadata = {
  title: "關於我們 | 龜山壓克力製造",
  description:
    "桃園龜山20年複合式壓克力製造商 — CNC、CO₂雷射、大裁板機、電腦裁板機、圓聚切割機等設備與製程介紹。",
};

const EQUIPMENT = [
  { name: "CNC 加工中心", desc: "精密銑切與異形加工，處理厚板與多層結構件" },
  { name: "CO₂ 雷射雕刻機", desc: "品牌LOGO雷雕、鏤空圖樣與精細切割" },
  { name: "大裁板機", desc: "整張2000×1000mm標準板一次開料，降低邊料浪費" },
  { name: "電腦壓克力裁板機", desc: "依排版程式自動下刀，刀縫3mm精度穩定" },
  { name: "圓聚切割機", desc: "圓弧、圓盤與轉角件成型" },
  { name: "噴漆與烤漆線", desc: "底座、鐵件與木作的表面處理與色彩配合" },
];

const CAPABILITIES = [
  { title: "複合式材料整合", desc: "壓克力、木工、鐵件、LED、噴漆在同一條線上整合，不必分包給多家廠商。" },
  { title: "量產與交期穩定", desc: "導入ERP工單與備料系統，從BOM展開、發料到完工入庫全程有數據可追。" },
  { title: "板材利用率最佳化", desc: "自研2D排版演算法，依零件尺寸自動比較9種板型，找出最省片數的開料方案。" },
  { title: "剩料回收管理", desc: "每次裁切產生的可用剩料登記入庫並分級，小批量案件優先吃剩料。" },
];

export default function AboutPage() {
  return (
    <div className="bg-white min-h-screen">
      <SiteHeader />

      <div className="max-w-4xl mx-auto px-6 py-14">
        <h1 className="text-3xl font-bold text-slate-900">關於我們</h1>
        <p className="text-slate-600 mt-5 leading-relaxed">
          我們位於桃園市龜山區，是一家擁有20年以上經驗的複合式壓克力展示架製造商。
          從彩妝品牌的櫃檯陳列架、酒商的高透光展示櫃、國際家電品牌的產品展示座，
          到零售通路的大型尿布架，我們的專長是把設計圖轉成可量產、耐用、且準時交貨的實體展示架。
        </p>
        <p className="text-slate-600 mt-4 leading-relaxed">
          近年我們把二十年累積的老師傅工藝，搭配自建的智慧製造 ERP 系統：
          報價、BOM、庫存、採購、工單、現場報工到裁切排版全部數位化，
          讓「做得出來」之外，也能回答客戶「什麼時候交、為什麼是這個價」。
        </p>

        <h2 className="text-xl font-semibold text-slate-800 mt-12">我們的能力</h2>
        <div className="grid sm:grid-cols-2 gap-5 mt-6">
          {CAPABILITIES.map((c) => (
            <div key={c.title} className="border border-slate-200 rounded-2xl p-5">
              <div className="font-medium text-slate-800">{c.title}</div>
              <p className="text-sm text-slate-500 mt-2 leading-relaxed">{c.desc}</p>
            </div>
          ))}
        </div>

        <h2 className="text-xl font-semibold text-slate-800 mt-12">設備介紹</h2>
        <div className="mt-6 divide-y divide-slate-100 border-y border-slate-100">
          {EQUIPMENT.map((e) => (
            <div key={e.name} className="py-4 sm:flex sm:gap-6">
              <div className="font-medium text-slate-800 sm:w-52 shrink-0">{e.name}</div>
              <p className="text-sm text-slate-500 mt-1 sm:mt-0 leading-relaxed">{e.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-12 bg-slate-50 rounded-2xl p-8 text-center">
          <p className="text-slate-700 font-medium">想討論您的展示架專案？</p>
          <p className="text-slate-500 text-sm mt-2">
            提供尺寸、材質與數量，我們會在1個工作日內回覆初步報價評估。
          </p>
          <Link
            href="/quote"
            className="inline-block mt-5 bg-slate-900 text-white px-6 py-3 rounded-full text-sm"
          >
            線上詢價
          </Link>
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}
