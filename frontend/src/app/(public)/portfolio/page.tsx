import Link from "next/link";
import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site/SiteHeader";
import { TypeDrawing, kindFromText } from "@/components/site/TypeDrawing";
import { listPublicCases } from "@/lib/publicApi";

export const metadata: Metadata = {
  title: "作品案例 | 龜山壓克力製造",
  description: "彩妝架、酒類展示櫃、家電展示架、尿布架 — 桃園龜山複合式壓克力展示架製造實績。",
};

export const revalidate = 60;

export default async function PortfolioListPage() {
  const cases = await listPublicCases();
  const industries = Array.from(new Set(cases.map((c) => c.industry).filter(Boolean) as string[]));

  return (
    <>
      <SiteHeader />
      <section className="site-wrap site-sec">
        <div className="sec-head">
          <div className="eyebrow">Selected Work</div>
          <h1 className="site-h2">作品案例</h1>
          <p className="site-lede">
            二十年來為彩妝、酒類、家電與嬰幼用品品牌製作的展示架。每一件都經過壓克力、木工、鐵件、LED 與噴漆的複合工法整合。
          </p>
          {industries.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {industries.map((ind) => (
                <span key={ind} className="tag" style={{ border: "1px solid var(--line-2)", padding: "5px 10px" }}>
                  {ind}
                </span>
              ))}
            </div>
          )}
        </div>

        {cases.length === 0 ? (
          <div className="panel cta">
            <h2>案例整理中</h2>
            <p>作品由後台「作品管理」發佈後會即時出現在這裡。若想先了解我們的製造能力，直接跟我們談需求最快。</p>
            <Link className="btn btn-led" href="/quote">
              直接與我們談需求 →
            </Link>
          </div>
        ) : (
          <div className="cases-3">
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
                <div className="spec-line">{[c.product_type, c.dimensions].filter(Boolean).join(" · ") || "—"}</div>
              </Link>
            ))}
          </div>
        )}
      </section>
      <SiteFooter />
    </>
  );
}
