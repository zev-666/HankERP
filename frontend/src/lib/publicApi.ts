/**
 * 官網公開 API 讀取工具（Server Component 專用）
 *
 * 設計重點：後端若尚未啟動或網路不通，這裡一律回傳空陣列而不是拋錯。
 * 原因：官網頁面在 `next build` 時會被預先渲染，若此時 fetch 直接拋錯，
 * 整個前端建置就會失敗——那會讓「後端沒開就不能建置前端」，在 CI 與
 * 本機開發都非常難用。改為降級為空清單，頁面顯示「案例即將上線」。
 */
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type PortfolioCase = {
  title: string;
  slug: string;
  industry: string | null;
  product_type: string | null;
  cover_image_url: string | null;
  dimensions: string | null;
};

export type PortfolioDetail = PortfolioCase & {
  client_name: string | null;
  materials: string | null;
  gallery_urls: string[];
  challenge: string | null;
  solution: string | null;
  result: string | null;
};

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${BASE_URL}${path}`, { next: { revalidate: 60 } });
    if (!res.ok) return fallback;
    const json = await res.json();
    return (json.data ?? fallback) as T;
  } catch {
    return fallback;
  }
}

export function listPublicCases(featuredOnly = false): Promise<PortfolioCase[]> {
  const qs = featuredOnly ? "?featured_only=true" : "";
  return getJson<PortfolioCase[]>(`/api/v1/public/portfolio${qs}`, []);
}

export function getPublicCase(slug: string): Promise<PortfolioDetail | null> {
  // Next.js 16 的動態路由參數是「未解碼」的原始路徑片段：
  // 網址 /portfolio/%E5%BD%A9%E5%A6%9D-123 拿到的 params.slug 就是
  // "%E5%BD%A9%E5%A6%9D-123" 而不是 "彩妝-123"。
  // 因為作品 slug 會含中文（_slugify 保留 一-鿿），若直接再 encodeURIComponent
  // 就會變成雙重編碼（%25E5%25BD%25A9…），後端查不到而整頁 404。
  // 先解碼再重新編碼，對已解碼的純 ASCII slug 也是安全的。
  let normalized = slug;
  try {
    normalized = decodeURIComponent(slug);
  } catch {
    /* 非法的百分比序列就用原值，交給後端回 404 */
  }
  return getJson<PortfolioDetail | null>(
    `/api/v1/public/portfolio/${encodeURIComponent(normalized)}`,
    null,
  );
}

export const PUBLIC_API_BASE = BASE_URL;
