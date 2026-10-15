/**
 * 永陛 & 進化 EVEREVO 標誌（2026-10-15 定案：方案 C「雙片疊合」）
 *
 * 兩片壓克力板錯位疊合：左上片＝永陛、右下片＝進化，重疊處最亮＝兩家合作。
 * tone="dark" 用在深色底（官網、ERP 側欄），tone="light" 用在白底（登入頁、文件）。
 * 小尺寸（≤32px）自動加粗線條，避免在分頁圖示大小時糊掉。
 * 分頁小圖示是另一份靜態檔：src/app/icon.svg（Next.js App Router 檔案慣例）。
 */
type Tone = "dark" | "light";

const COLORS: Record<Tone, { ink: string; edge: string }> = {
  dark: { ink: "#E7EEF1", edge: "#6FE0CE" },
  light: { ink: "#0C1319", edge: "#1F8A7C" },
};

export function BrandMark({
  size = 28,
  tone = "dark",
  label,
}: {
  size?: number;
  tone?: Tone;
  /** 有傳就當成有意義的圖片（role="img"）；沒傳就是裝飾，旁邊一定有文字品牌名 */
  label?: string;
}) {
  const { ink, edge } = COLORS[tone];
  const sw = size <= 32 ? 3.4 : 1.8;
  const a11y = label
    ? { role: "img" as const, "aria-label": label }
    : { "aria-hidden": true as const };
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" {...a11y} style={{ flex: "none" }}>
      <rect x="6" y="6" width="34" height="42" rx="3" fill="none" stroke={ink} strokeWidth={sw} />
      <rect
        x="24" y="16" width="34" height="42" rx="3"
        fill={edge} fillOpacity={0.08} stroke={edge} strokeWidth={sw}
      />
      {/* 兩片重疊的區域：x 24–40、y 16–48，內縮半個線寬 */}
      <rect
        x={24 + sw / 2} y={16 + sw / 2} width={16 - sw} height={32 - sw}
        fill={edge} fillOpacity={0.62}
      />
    </svg>
  );
}

