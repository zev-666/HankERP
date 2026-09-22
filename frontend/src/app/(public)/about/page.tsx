import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site/SiteHeader";

export const metadata: Metadata = {
  title: "關於我們 | 龜山壓克力製造",
  description:
    "桃園龜山 20 年複合式壓克力製造商 — CNC、CO₂雷射、大裁板機、電腦裁板機、圓聚切割機等設備與製程介紹。",
};

const CAPABILITIES = [
  { t: "複合式材料整合", d: "壓克力、木工、鐵件、LED、噴漆在同一條線上整合，不必分包給多家廠商。" },
  { t: "師傅手工收尾", d: "拋光收邊、燈光校色、整檯試組，機器做不到的最後一哩，仍由老師傅逐台過手。" },
  { t: "板材利用率最佳化", d: "自建 2D 排版引擎，依零件尺寸比較 9 種板型，找出最省片數的開料方案。" },
  { t: "剩料回收管理", d: "每次裁切的可用餘料登記入庫並分 A / B / C 級，小批量訂單優先使用。" },
];

const EQUIPMENT = [
  { n: "CNC 加工中心", d: "精密銑切與異形加工，處理厚板與多層結構件" },
  { n: "CO₂ 雷射雕刻機", d: "品牌 LOGO 雷雕、鏤空圖樣與精細切割" },
  { n: "大裁板機", d: "整張 2000×1000mm 標準板一次開料，降低邊料浪費" },
  { n: "電腦壓克力裁板機", d: "依排版程式自動下刀，刀縫 3mm 精度穩定" },
  { n: "圓聚切割機", d: "圓弧、圓盤與轉角件成型" },
  { n: "噴漆與烤漆線", d: "底座、鐵件與木作的表面處理與色彩配合" },
];

export default function AboutPage() {
  return (
    <>
      <SiteHeader />
      <section className="site-wrap site-sec" style={{ maxWidth: 960 }}>
        <div className="sec-head">
          <div className="eyebrow">About</div>
          <h1 className="site-h2">精度靠機器，質感靠師傅的手</h1>
        </div>
        <div className="prose">
          <p>
            我們位於桃園市龜山區，是一家擁有二十年以上經驗的複合式壓克力展示架製造商。
            從彩妝品牌的櫃檯陳列架、酒商的高透光展示櫃、國際家電品牌的產品展示座，
            到零售通路的大型尿布架，我們的專長是把設計圖變成可量產、耐用、準時交貨的實體展示架。
          </p>
          <p>
            近年我們把二十年累積的工藝，搭配自建的智慧製造系統：報價、BOM、庫存、採購、工單、
            現場報工到裁切排版全部數位化，讓「做得出來」之外，也能回答客戶「什麼時候交、為什麼是這個價」。
          </p>
        </div>

        <div className="sec-head" style={{ marginTop: 56 }}>
          <div className="eyebrow">Capabilities</div>
          <h2 className="site-h2" style={{ fontSize: "clamp(22px,3vw,30px)" }}>
            我們的能力
          </h2>
        </div>
        <div className="cases" style={{ gridTemplateColumns: "repeat(auto-fit,minmax(min(100%,240px),1fr))" }}>
          {CAPABILITIES.map((c) => (
            <div key={c.t} className="panel case">
              <h3>{c.t}</h3>
              <p style={{ margin: 0, fontSize: 14, color: "var(--mute)", lineHeight: 1.75 }}>{c.d}</p>
            </div>
          ))}
        </div>

        <div className="sec-head" style={{ marginTop: 56 }}>
          <div className="eyebrow">Equipment</div>
          <h2 className="site-h2" style={{ fontSize: "clamp(22px,3vw,30px)" }}>
            設備
          </h2>
        </div>
        <dl className="spec-grid">
          {EQUIPMENT.map((e) => (
            <div key={e.n} className="spec-row" style={{ flexDirection: "column", alignItems: "flex-start", gap: 6 }}>
              <dt style={{ color: "var(--paper)", fontWeight: 700, fontSize: 15 }}>{e.n}</dt>
              <dd style={{ textAlign: "left", fontFamily: "var(--sans)", fontSize: 13.5, color: "var(--mute)" }}>{e.d}</dd>
            </div>
          ))}
        </dl>

        <div className="panel cta" style={{ marginTop: 56 }}>
          <h2>想討論您的展示架專案？</h2>
          <p>提供尺寸、材質與數量，我們會在一個工作日內回覆初步報價評估。</p>
          <Link className="btn btn-led" href="/quote">
            線上詢價 →
          </Link>
        </div>
      </section>
      <SiteFooter />
    </>
  );
}
