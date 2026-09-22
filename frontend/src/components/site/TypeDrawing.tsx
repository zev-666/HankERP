/**
 * 展示架結構立面線稿。實拍照片到位前，作品卡片用它代替圖片——
 * 這是示意圖而非假照片，頁面上會明確標示「實拍照片整理中」。
 */
type Kind = "cosmetics" | "spirits" | "appliance" | "baby";

const S = { fill: "none", stroke: "#3FA394", strokeWidth: 1.1 } as const;
const BASE = "#263A45";
const DIM = "#1F4F49";
const EDGE = "#6FE0CE";
const LED = "#F0A93C";

export function kindFromText(text?: string | null): Kind {
  const t = text ?? "";
  if (/酒/.test(t)) return "spirits";
  if (/家電|電器|牙刷/.test(t)) return "appliance";
  if (/尿布|嬰|幼/.test(t)) return "baby";
  return "cosmetics";
}

export function TypeDrawing({ kind }: { kind: Kind }) {
  return (
    <svg viewBox="0 0 120 92" {...S} aria-hidden="true">
      {kind === "cosmetics" && (
        <>
          <path d="M14 86h92" stroke={BASE} />
          <rect x="22" y="62" width="76" height="24" />
          <rect x="30" y="44" width="60" height="18" />
          <rect x="38" y="26" width="44" height="18" />
          <path d="M46 26V14h28v12" stroke={EDGE} />
          <path d="M30 62h60M38 44h44" stroke={DIM} />
          <path d="M24 20h72" stroke={LED} strokeDasharray="2 3" />
        </>
      )}
      {kind === "spirits" && (
        <>
          <path d="M14 86h92" stroke={BASE} />
          <rect x="34" y="10" width="52" height="76" />
          <path d="M34 30h52M34 49h52M34 68h52" stroke={DIM} />
          <path d="M40 18h8M52 18h8M64 18h8M76 18h4" stroke={EDGE} strokeWidth={2.4} />
          <path d="M34 10h52" stroke={LED} />
          <path d="M40 86v-4M80 86v-4" stroke={BASE} />
        </>
      )}
      {kind === "appliance" && (
        <>
          <path d="M14 86h92" stroke={BASE} />
          <rect x="18" y="66" width="84" height="20" />
          <rect x="44" y="34" width="32" height="32" />
          <path d="M52 34V22h16v12" stroke={EDGE} />
          <circle cx="60" cy="50" r="7" stroke={DIM} />
          <path d="M18 76h84" stroke={DIM} />
          <path d="M28 66v-6M92 66v-6" stroke={LED} />
        </>
      )}
      {kind === "baby" && (
        <>
          <path d="M8 86h104" stroke={BASE} />
          <rect x="16" y="20" width="88" height="66" />
          <path d="M16 42h88M16 64h88" stroke={DIM} />
          <path d="M45 20v66M74 20v66" stroke={DIM} />
          <path d="M16 20h88" stroke={EDGE} />
          <path d="M24 14h72" stroke={LED} strokeDasharray="2 3" />
        </>
      )}
    </svg>
  );
}
