import type { MetadataRoute } from "next";
import { listPublicCases } from "@/lib/publicApi";

/**
 * 動態 sitemap：公開頁面 + 後台實際發佈的每一則作品案例。
 * SITE_URL 未設定時退回 localhost，僅影響本機預覽，不會讓建置失敗。
 */
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE_URL}/portfolio`, changeFrequency: "weekly", priority: 0.9 },
    { url: `${SITE_URL}/about`, changeFrequency: "monthly", priority: 0.7 },
    { url: `${SITE_URL}/quote`, changeFrequency: "monthly", priority: 0.8 },
  ];

  const cases = await listPublicCases();
  return [
    ...staticPages,
    ...cases.map((c) => ({
      url: `${SITE_URL}/portfolio/${c.slug}`,
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
  ];
}
