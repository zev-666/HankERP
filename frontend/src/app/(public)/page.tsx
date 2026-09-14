import Link from "next/link";
import { SiteHeader, SiteFooter } from "@/components/site/SiteHeader";
import { listPublicCases } from "@/lib/publicApi";

const PROCESSES = [
  "CNC 數位切割",
  "CO₂ 雷射雕刻",
  "電腦壓克力裁板",
  "圓弧切割",
  "噴漆處理",
  "LED整合",
];

export const revalidate = 60;

export default async function HomePage() {
  // v2.0：改為讀取後台實際發佈的作品。
  // 先前此處是寫死在程式碼裡的 4 筆假資料（const CASES = [...]），
  // 後台無論發佈什麼，官網永遠顯示同樣 4 筆，等同一個永遠對不上的展示櫥窗。
  const cases = (await listPublicCases()).slice(0, 4);

  return (
    <div className="bg-white">
      <SiteHeader />

      <section className="max-w-6xl mx-auto px-6 py-20 text-center">
        <div className="text-amber-600 text-sm font-medium mb-3">
          桃園龜山 · 20年複合式壓克力製造經驗
        </div>
        <h1 className="text-4xl md:text-5xl font-bold text-slate-900 leading-tight">
          從老師傅工藝，
          <br />
          到智慧製造展示架
        </h1>
        <p className="text-slate-500 mt-6 max-w-xl mx-auto">
          壓克力 × 木工 × 鐵件 × LED × 噴漆，複合式工法打造國際品牌信賴的展示架製造夥伴
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link
            href="/quote"
            className="bg-slate-900 text-white px-6 py-3 rounded-full text-sm font-medium hover:bg-slate-700"
          >
            立即詢價
          </Link>
          <Link
            href="/portfolio"
            className="border border-slate-300 px-6 py-3 rounded-full text-sm font-medium text-slate-600 hover:border-slate-400"
          >
            查看作品
          </Link>
        </div>
      </section>

      <section id="cases" className="max-w-6xl mx-auto px-6 py-16">
        <div className="flex items-end justify-between mb-8">
          <h2 className="text-2xl font-semibold text-slate-800">合作案例</h2>
          {cases.length > 0 && (
            <Link href="/portfolio" className="text-sm text-slate-500 hover:text-slate-800">
              查看全部 →
            </Link>
          )}
        </div>

        {cases.length === 0 ? (
          <div className="border border-dashed border-slate-300 rounded-2xl p-10 text-center">
            <p className="text-slate-500 text-sm">
              案例即將上線。若您想先了解我們的製造能力，歡迎
              <Link href="/quote" className="text-slate-800 underline underline-offset-4 mx-1">
                線上詢價
              </Link>
              與我們聯繫。
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {cases.map((c) => (
              <Link
                key={c.slug}
                href={`/portfolio/${c.slug}`}
                className="border border-slate-200 rounded-2xl p-6 hover:shadow-lg transition-shadow block"
              >
                {c.industry && (
                  <span className="text-xs bg-amber-50 text-amber-700 px-2.5 py-1 rounded-full font-medium">
                    {c.industry}
                  </span>
                )}
                <h3 className="text-lg font-semibold text-slate-800 mt-3">{c.title}</h3>
                <p className="text-sm text-slate-500 mt-2 leading-relaxed">
                  {[c.product_type, c.dimensions].filter(Boolean).join(" · ") || "查看詳情"}
                </p>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section id="process" className="bg-slate-50 py-16">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-2xl font-semibold text-slate-800 mb-8">製造工法與設備</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {PROCESSES.map((p) => (
              <div key={p} className="bg-white rounded-xl p-5 text-center border border-slate-100">
                <div className="text-sm font-medium text-slate-700">{p}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-semibold text-slate-800 mb-4">關於我們</h2>
        <p className="text-slate-500 max-w-2xl leading-relaxed">
          我們位於桃園龜山，擁有超過20年壓克力加工經驗，專精複合式材料製程，
          為彩妝、家電、酒類、嬰幼用品等國際品牌打造客製化展示架，並導入數位化智慧製造系統，
          確保每一件作品的品質與交期穩定。
        </p>
        <Link
          href="/about"
          className="inline-block mt-5 text-sm text-slate-700 underline underline-offset-4"
        >
          更多關於我們與設備介紹 →
        </Link>
      </section>

      <SiteFooter />
    </div>
  );
}
