import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site/SiteHeader";
import { TypeDrawing, kindFromText } from "@/components/site/TypeDrawing";
import { getPublicCase } from "@/lib/publicApi";

export const revalidate = 60;

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const c = await getPublicCase(slug);
  if (!c) return { title: "找不到此案例 | 龜山壓克力製造" };
  return {
    title: `${c.title} | 龜山壓克力製造`,
    description:
      [c.industry, c.product_type, c.dimensions].filter(Boolean).join(" · ") ||
      `${c.title} — 桃園龜山壓克力展示架製造實績`,
    openGraph: c.cover_image_url ? { images: [c.cover_image_url] } : undefined,
  };
}

export default async function PortfolioDetailPage({ params }: Props) {
  const { slug } = await params;
  const c = await getPublicCase(slug);
  if (!c) notFound();

  const specs = (
    [
      ["客戶", c.client_name],
      ["產業", c.industry],
      ["產品類型", c.product_type],
      ["尺寸", c.dimensions],
      ["材質", c.materials],
    ] as [string, string | null][]
  ).filter(([, v]) => Boolean(v)) as [string, string][];

  const sections = (
    [
      ["客戶挑戰", c.challenge],
      ["我們的作法", c.solution],
      ["成果", c.result],
    ] as [string, string | null][]
  ).filter(([, v]) => Boolean(v)) as [string, string][];

  return (
    <>
      <SiteHeader />
      <article className="site-wrap site-sec" style={{ maxWidth: 960 }}>
        <Link href="/portfolio" className="back">
          ← 回作品案例
        </Link>
        <div className="sec-head" style={{ marginTop: 22 }}>
          {c.industry && <div className="eyebrow">{c.industry}</div>}
          <h1 className="site-h2">{c.title}</h1>
        </div>

        <div className="panel" style={{ padding: 16 }}>
          <div className="draw" style={{ aspectRatio: "16/9" }}>
            {c.cover_image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={c.cover_image_url} alt={c.title} />
            ) : (
              <div style={{ width: "min(420px,100%)" }}>
                <TypeDrawing kind={kindFromText(`${c.industry ?? ""}${c.title}`)} />
              </div>
            )}
          </div>
        </div>

        {specs.length > 0 && (
          <dl className="kv" style={{ marginTop: 24 }}>
            {specs.map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        )}

        {sections.length > 0 && (
          <div style={{ display: "grid", gap: 30, marginTop: 44 }}>
            {sections.map(([h, body]) => (
              <div key={h} className="prose">
                <div className="eyebrow" style={{ marginBottom: 10 }}>
                  {h}
                </div>
                <p style={{ whiteSpace: "pre-line" }}>{body}</p>
              </div>
            ))}
          </div>
        )}

        {c.gallery_urls?.length > 0 && (
          <div className="cases-3" style={{ marginTop: 40 }}>
            {c.gallery_urls.map((url, i) => (
              <div key={i} className="draw">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={url} alt={`${c.title} 細節 ${i + 1}`} />
              </div>
            ))}
          </div>
        )}

        <div className="panel cta" style={{ marginTop: 56 }}>
          <h2>有類似的展示架需求？</h2>
          <p>給我們尺寸、材質與數量，一個工作日內回覆初步報價評估。</p>
          <Link className="btn btn-led" href="/quote">
            線上詢價 →
          </Link>
        </div>
      </article>
      <SiteFooter />
    </>
  );
}
