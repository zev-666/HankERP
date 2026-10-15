/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 資安：原本 images.remotePatterns 用萬用字元 https://** 允許從任何網域載入圖片，
  // 但目前程式碼完全沒有使用 next/image 元件，屬於規劃階段殘留設定，已移除避免不必要的攻擊面。
  // 未來若需要顯示外部圖片（例如MinIO/S3），請改為明確列出實際使用的網域，勿使用萬用字元。

  // 資安：加上標準安全標頭，防止點擊劫持(clickjacking)、MIME類型嗅探攻擊等
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          // HSTS（v2.3.5 調整）：瀏覽器收到後，在 max-age 期間內只肯用 HTTPS 連這個網域。
          // 原本是 2 年＋includeSubDomains＋preload——剛上線就設這麼長，任何子網域或憑證設定出錯
          // 都無法回頭。先用 1 天、不含子網域、不 preload；上線穩定一個月後再逐步拉長。
          {
            key: "Strict-Transport-Security",
            value: "max-age=86400",
          },
        ],
      },
    ];
  },
};
module.exports = nextConfig;
