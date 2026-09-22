import Link from "next/link";
import { SiteHeader, SiteFooter } from "@/components/site/SiteHeader";
import { NestingDiagram } from "@/components/site/NestingDiagram";
import { TypeDrawing, kindFromText } from "@/components/site/TypeDrawing";
import { listPublicCases } from "@/lib/publicApi";

export const revalidate = 60;

const STEPS = [
  { s: "01 / ACRYLIC", t: "壓克力裁切", d: "大裁板機開料，CNC 與 CO₂ 雷射成型。刀縫 3mm 進排版計算，不靠師傅估。" },
  { s: "02 / WOOD", t: "木作底座", d: "承重結構與貼皮處理，與壓克力介面預留收縮餘量。" },
  { s: "03 / METAL", t: "鐵件支撐", d: "高櫃與懸臂結構的骨架，折彎與焊接後做防鏽。" },
  { s: "04 / LED", t: "燈光整合", d: "燈條嵌入式固定於 CNC 一體成型槽位，避免壓克力與燈具之間出現縫隙。" },
  { s: "05 / FINISH", t: "噴漆與組裝", d: "色彩比對、表面處理、整檯試組，出貨前逐台通電確認。" },
];

// 後台尚無已發佈作品時顯示的「類型示意」——尺寸與材質為實際出貨規格
const TYPE_CARDS = [
  { tag: "COSMETICS", title: "櫃檯彩妝陳列架", spec: "三層階梯 · W450×D300×H600", mat: "3mm 透明壓克力 + LED 頂打光", kind: "cosmetics" as const },
  { tag: "SPIRITS", title: "酒類高透光展示櫃", spec: "四層 · W520×D340×H1450", mat: "5mm 壓克力 + 鐵件骨架 + 側發光", kind: "spirits" as const },
  { tag: "APPLIANCE", title: "家電產品體驗座", spec: "互動式 · W900×D400×H520", mat: "壓克力 + 木作底座 + 通電測試位", kind: "appliance" as const },
  { tag: "BABY CARE", title: "量販通路尿布陳列架", spec: "九格 · W1200×D450×H1600", mat: "耐重 80kg / 層 · 符合通路規格", kind: "baby" as const },
];

const SPECS: [string, string][] = [
  ["一才", "300 × 300 mm"],
  ["標準板材", "2000 × 1000 mm"],
  ["一張板", "22.2 才"],
  ["裁切刀縫", "3.0 mm"],
  ["常備板厚", "2 / 3 / 5 / 8 / 10 mm"],
  ["剩料分級", "A / B / C"],
];

export default async function HomePage() {
  // 讀取後台實際發佈的作品；後端連不到時回傳空陣列，頁面改顯示類型示意
  const cases = (await listPublicCases()).slice(0, 4);

  return (
    <>
      <SiteHeader />

      <header className="site-wrap hero">
        <div className="hero-grid">
          <div>
            <div className="eyebrow">桃園龜山 · 20 年複合式製程</div>
            <h1>
              精度靠機器，
              <br />
              <em>質感靠師傅的手</em>。
            </h1>
            <p>
              二十年複合式製程，為國際彩妝、酒類與家電品牌製作展示架。 CNC 與雷射負責毫米級的開料；
              最後那道拋光收邊、燈光校色與整檯試組，仍然是老師傅一台一台過手。
            </p>
            <div className="hero-cta">
              <Link className="btn btn-led" href="/quote">
                開始詢價 →
              </Link>
              <Link className="btn btn-ghost" href="/portfolio">
                查看作品
              </Link>
            </div>
          </div>

          <div className="panel nest">
            <div className="nest-head">
              <span>NESTING · 彩妝展示架 A 型</span>
              <span>
                板材利用率 <span className="val">88.2%</span>
              </span>
            </div>
            <NestingDiagram />
            <div className="nest-foot">
              <span>SHEET 2000 × 1000 mm</span>
              <span>KERF 3.0 mm</span>
              <span>PARTS 17</span>
              <span>SCRAP 11.8%</span>
            </div>
          </div>
        </div>
      </header>

      <div className="stats">
        <div className="site-wrap" style={{ paddingInline: 0 }}>
          <div className="stats-in">
            <div className="stat">
              <div className="n">20<small>年</small></div>
              <div className="k">複合式壓克力製造經驗</div>
            </div>
            <div className="stat">
              <div className="n">5<small>種</small></div>
              <div className="k">材料整合於同一條產線</div>
            </div>
            <div className="stat">
              <div className="n">88.2<small>%</small></div>
              <div className="k">排版引擎的板材利用率</div>
            </div>
            <div className="stat">
              <div className="n">3.0<small>mm</small></div>
              <div className="k">刀縫計入排版，不靠目測</div>
            </div>
          </div>
        </div>
      </div>

      <section id="process" className="site-wrap site-sec">
        <div className="sec-head">
          <div className="eyebrow">Process</div>
          <h2 className="site-h2">五種材料，一條產線</h2>
          <p className="site-lede">
            展示架很少只是壓克力。難的是把五種材料的公差、工序與交期壓在同一張工單上——這是我們不分包的原因。
          </p>
        </div>
        <div className="flow">
          {STEPS.map((st) => (
            <div className="step" key={st.s}>
              <div className="s">{st.s}</div>
              <h3>{st.t}</h3>
              <p>{st.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="cases" className="site-wrap site-sec">
        <div className="sec-head">
          <div className="eyebrow">Selected Work</div>
          <h2 className="site-h2">做過的東西</h2>
          <p className="site-lede">彩妝、酒類、家電、嬰幼用品——四類通路，四種完全不同的耐重與陳列邏輯。</p>
        </div>

        {cases.length > 0 ? (
          <div className="cases">
            {cases.map((c) => (
              <Link key={c.slug} href={`/portfolio/${c.slug}`} className="panel case">
                <div className="draw">
                  {c.cover_image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={c.cover_image_url} alt={c.title} />
                  ) : (
                    <TypeDrawing kind={kindFromText(`${c.industry ?? ""}${c.title}`)} />
                  )}
                </div>
                {c.industry && <div className="tag">{c.industry}</div>}
                <h3>{c.title}</h3>
                <div className="spec-line">
                  {[c.product_type, c.dimensions].filter(Boolean).join(" · ") || "查看詳情 →"}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <>
            <div className="cases">
              {TYPE_CARDS.map((c) => (
                <article key={c.tag} className="panel case">
                  <div className="draw">
                    <TypeDrawing kind={c.kind} />
                  </div>
                  <div className="tag">{c.tag}</div>
                  <h3>{c.title}</h3>
                  <div className="spec-line">
                    {c.spec}
                    <br />
                    {c.mat}
                  </div>
                </article>
              ))}
            </div>
            <p className="note">實拍照片整理中。上方為各類型的結構立面示意，尺寸與材質為實際出貨規格。</p>
          </>
        )}
      </section>

      <section id="spec" className="site-wrap site-sec">
        <div className="sec-head">
          <div className="eyebrow">Specification</div>
          <h2 className="site-h2">我們用的單位</h2>
          <p className="site-lede">報價談的是「才」，生產談的是「毫米」。把兩邊對起來，估價才不會失準。</p>
        </div>
        <dl className="spec-grid">
          {SPECS.map(([k, v]) => (
            <div className="spec-row" key={k}>
              <dt>{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
        <p className="note">
          剩料不是廢料。5×5cm 以上的餘料都會登記入庫分級，小批量訂單優先吃剩料——這是我們敢報比較低價的地方。
        </p>
      </section>

      <section id="about" className="site-wrap site-sec">
        <div className="sec-head">
          <div className="eyebrow">About</div>
          <h2 className="site-h2">老師傅的手，加上算得清楚的帳</h2>
        </div>
        <p className="site-lede" style={{ maxWidth: "62ch", fontSize: 16.5 }}>
          我們在桃園市龜山區，二十年來做的都是同一件事：把設計圖變成能量產、耐用、準時交貨的展示架。
          近年我們把工藝背後的流程整個數位化——報價、BOM、庫存、採購、工單、現場報工到裁切排版，
          每一步都留下數據。所以除了「做得出來」，我們也答得出「什麼時候交、為什麼是這個價」。
        </p>
        <Link href="/about" className="back" style={{ display: "inline-block", marginTop: 20 }}>
          設備與能力介紹 →
        </Link>
      </section>

      <section className="site-wrap site-sec" style={{ paddingTop: 0 }}>
        <div className="panel cta">
          <div className="eyebrow">Request a Quote</div>
          <h2>把尺寸、材質、數量給我們</h2>
          <p>一個工作日內回覆初步報價評估。圖面還沒定案也可以先談，我們會告訴你哪些做法比較省。</p>
          <div className="cta-row">
            <Link className="btn btn-led" href="/quote">
              線上詢價 →
            </Link>
            <span className="cta-note">週一至週五 08:30–17:30</span>
          </div>
        </div>
      </section>

      <SiteFooter />
    </>
  );
}
