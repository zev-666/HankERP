import type { MetadataRoute } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

/**
 * ERP 後台（/erp）、現場報工（/mes）與登入頁不應被搜尋引擎索引。
 * 這是 SEO 設定，不是存取控制——真正的權限仍由後端 JWT 把關。
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/erp/", "/mes/", "/login"],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
