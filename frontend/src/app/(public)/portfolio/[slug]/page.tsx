import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { SiteHeader, SiteFooter } from "@/components/site/SiteHeader";
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

function Section({ title, body }: { title: string; body: string | null }) {
  if (!body) return null;
  return (
    <div>
      <h2 className="text-sm font-semibold text-slate-800 tracking-wide">{title}</h2>
      <p className="text-slate-600 mt-2 leading-relaxed whitespace-pre-line">{body}</p>
    </div>
  );
}

export default async function PortfolioDetailPage({ params }: Props) {
  const { slug } = await params;
  const c = await getPublicCase(slug);
  if (!c) notFound();

  const specs = [
    ["客戶", c.client_name],
    ["產業", c.industry],
    ["產品類型", c.product_type],
    ["尺寸", c.dimensions],
    ["材質", c.materials],
  ].filter(([, v]) => Boolean(v)) as [string, string][];

  return (
    <div className="bg-white min-h-screen">
      <SiteHeader />

      <article className="max-w-4xl mx-auto px-6 py-14">
        <Link href="/portfolio" className="text-sm text-slate-500 hover:text-slate-800">
          ← 回作品案例
        </Link>

        <h1 className="text-3xl font-bold text-slate-900 mt-4">{c.title}</h1>

        {c.cover_image_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={c.cover_image_url}
            alt={c.title}
            className="w-full rounded-2xl mt-8 border border-slate-100"
          />
        )}

        {specs.length > 0 && (
          <dl className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-4 mt-8 border-y border-slate-100 py-6">
            {specs.map(([k, v]) => (
              <div key={k}>
                <dt className="text-xs text-slate-400">{k}</dt>
                <dd className="text-sm text-slate-700 mt-1">{v}</dd>
              </div>
            ))}
          </dl>
        )}

        <div className="space-y-8 mt-8">
          <Section title="客戶挑戰" body={c.challenge} />
          <Section title="我們的作法" body={c.solution} />
          <Section title="成果" body={c.result} />
        </div>

        {c.gallery_urls?.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-10">
            {c.gallery_urls.map((url, i) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={i}
                src={url}
                alt={`${c.title} 細節 ${i + 1}`}
                className="rounded-xl border border-slate-100"
              />
            ))}
          </div>
        )}

        <div className="mt-12 bg-slate-50 rounded-2xl p-8 text-center">
          <p className="text-slate-700 font-medium">有類似的展示架需求？</p>
          <Link
            href="/quote"
            className="inline-block mt-4 bg-slate-900 text-white px-6 py-3 rounded-full text-sm"
          >
            線上詢價
          </Link>
        </div>
      </article>

      <SiteFooter />
    </div>
  );
}
