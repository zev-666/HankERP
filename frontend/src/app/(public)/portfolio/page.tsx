import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site/SiteHeader";
import { listPublicCases } from "@/lib/publicApi";

export const metadata: Metadata = {
  title: "作品案例 | 龜山壓克力製造",
  description:
    "彩妝架、酒類展示櫃、家電展示架、尿布架 — 桃園龜山複合式壓克力展示架製造實績。",
};

export const revalidate = 60;

export default async function PortfolioListPage() {
  // v2.0 新增：先前 (public)/portfolio/ 只是一個空資料夾，
  // 官網其實沒有任何作品展示頁可以點進去。
  const cases = await listPublicCases();

  const industries = Array.from(
    new Set(cases.map((c) => c.industry).filter(Boolean) as string[]),
  );

  return (
    <div className="bg-white min-h-screen">
      <SiteHeader />

      <div className="max-w-6xl mx-auto px-6 py-14">
        <h1 className="text-3xl font-bold text-slate-900">作品案例</h1>
        <p className="text-slate-500 mt-3 max-w-2xl leading-relaxed">
          20年來為彩妝、酒類、家電與嬰幼用品品牌製作的展示架實績。
          每一件都經過壓克力、木工、鐵件、LED與噴漆的複合工法整合。
        </p>

        {industries.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-6">
            {industries.map((ind) => (
              <span
                key={ind}
                className="text-xs bg-slate-100 text-slate-600 px-3 py-1.5 rounded-full"
              >
                {ind}
              </span>
            ))}
          </div>
        )}

        {cases.length === 0 ? (
          <div className="border border-dashed border-slate-300 rounded-2xl p-12 text-center mt-10">
            <p className="text-slate-500 text-sm">
              目前尚無已發佈的案例。作品由後台「作品管理」發佈後會即時出現在這裡。
            </p>
            <Link
              href="/quote"
              className="inline-block mt-5 bg-slate-900 text-white px-5 py-2.5 rounded-full text-sm"
            >
              直接與我們談需求
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-10">
            {cases.map((c) => (
              <Link
                key={c.slug}
                href={`/portfolio/${c.slug}`}
                className="group border border-slate-200 rounded-2xl overflow-hidden hover:shadow-lg transition-shadow"
              >
                <div className="aspect-[4/3] bg-slate-100 flex items-center justify-center overflow-hidden">
                  {c.cover_image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={c.cover_image_url}
                      alt={c.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                    />
                  ) : (
                    <span className="text-slate-300 text-sm">尚無圖片</span>
                  )}
                </div>
                <div className="p-5">
                  {c.industry && (
                    <span className="text-xs bg-amber-50 text-amber-700 px-2.5 py-1 rounded-full font-medium">
                      {c.industry}
                    </span>
                  )}
                  <h2 className="text-base font-semibold text-slate-800 mt-3">{c.title}</h2>
                  <p className="text-sm text-slate-500 mt-1.5">
                    {[c.product_type, c.dimensions].filter(Boolean).join(" · ") || "—"}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <SiteFooter />
    </div>
  );
}
