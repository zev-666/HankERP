/**
 * 瀏覽器呼叫後端 API 的網址（建置期寫死）。
 *
 * - 一般情況：NEXT_PUBLIC_API_URL 是完整網址（本機 http://localhost:8000、正式站 https://api.everevo.com.tw）。
 * - 離線版（v2.3.11，docker-compose.offline.yml）：設成 "same-origin"，API 走跟網頁相同的網址，
 *   由 next.config.js 的 rewrites 把 /api/* 轉給後端容器。這樣同一份建置在
 *   http://localhost:3000 和區域網路的 http://<主機IP>:3000 都能用，不必把 IP 寫死。
 */
const RAW = process.env.NEXT_PUBLIC_API_URL;

export const API_SAME_ORIGIN = RAW === "same-origin";
export const API_BASE_URL = API_SAME_ORIGIN ? "" : RAW || "http://localhost:8000";
