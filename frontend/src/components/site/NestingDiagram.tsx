"use client";
import { useEffect, useRef } from "react";

/**
 * 首頁主視覺：一張 2000×1000mm 標準壓克力板的實際排版圖。
 *
 * 17 個零件、刀縫 3mm，零件面積合計 1,764,800 mm² ÷ 板材 2,000,000 mm² = 88.2%。
 * 數字是依下方座標實算，不是裝飾用的假數據——改零件時請同步更新利用率文字。
 */
const SHEET_W = 2000;
const SHEET_H = 1000;
const PARTS = [
  { x: 0, y: 0, w: 300, h: 600 },
  { x: 303, y: 0, w: 300, h: 600 },
  { x: 606, y: 0, w: 450, h: 600 },
  { x: 1059, y: 0, w: 460, h: 300 },
  { x: 1059, y: 303, w: 460, h: 300 },
  { x: 1522, y: 0, w: 300, h: 120 },
  { x: 1522, y: 123, w: 440, h: 60 },
  { x: 1522, y: 186, w: 440, h: 60 },
  { x: 0, y: 603, w: 440, h: 280 },
  { x: 443, y: 603, w: 440, h: 280 },
  { x: 886, y: 603, w: 440, h: 280 },
  { x: 1329, y: 603, w: 330, h: 280 },
  { x: 1662, y: 603, w: 330, h: 280 },
  { x: 0, y: 886, w: 490, h: 110 },
  { x: 493, y: 886, w: 490, h: 110 },
  { x: 986, y: 886, w: 490, h: 110 },
  { x: 1479, y: 886, w: 490, h: 110 },
];
const PAD = 46;

export function NestingDiagram() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let scale = 1;
    let raf = 0;

    const layout = () => {
      const cssW = Math.max(160, (cv.parentElement?.clientWidth ?? 600) - 32);
      scale = (cssW - PAD * 2) / SHEET_W;
      const cssH = SHEET_H * scale + PAD * 2;
      cv.style.width = `${cssW}px`;
      cv.style.height = `${cssH}px`;
      cv.width = Math.round(cssW * dpr);
      cv.height = Math.round(cssH * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = (progress: number) => {
      const W = cv.width / dpr;
      const H = cv.height / dpr;
      const sw = SHEET_W * scale;
      const sh = SHEET_H * scale;
      ctx.clearRect(0, 0, W, H);

      ctx.fillStyle = "rgba(17,27,34,.9)";
      ctx.fillRect(PAD, PAD, sw, sh);
      ctx.strokeStyle = "#263A45";
      ctx.lineWidth = 1;
      ctx.strokeRect(PAD + 0.5, PAD + 0.5, sw, sh);

      ctx.font = '500 10px "IBM Plex Mono", monospace';
      ctx.fillStyle = "#5D717C";
      ctx.textAlign = "center";
      ctx.fillText("2000 mm", PAD + sw / 2, PAD - 16);
      ctx.save();
      ctx.translate(PAD - 18, PAD + sh / 2);
      ctx.rotate(-Math.PI / 2);
      ctx.fillText("1000 mm", 0, 0);
      ctx.restore();

      ctx.strokeStyle = "#1C2A33";
      ctx.beginPath();
      ctx.moveTo(PAD, PAD - 9);
      ctx.lineTo(PAD + sw, PAD - 9);
      ctx.moveTo(PAD - 11, PAD);
      ctx.lineTo(PAD - 11, PAD + sh);
      ctx.stroke();

      ctx.textAlign = "left";
      PARTS.forEach((p, i) => {
        const appear = i / PARTS.length;
        const a = progress <= appear ? 0 : Math.min(1, (progress - appear) / 0.22);
        if (a <= 0) return;
        const x = PAD + p.x * scale;
        const y = PAD + p.y * scale;
        const w = p.w * scale;
        const h = p.h * scale;

        ctx.fillStyle = `rgba(111,224,206,${0.055 * a})`;
        ctx.fillRect(x, y, w, h);

        ctx.save();
        ctx.shadowColor = `rgba(111,224,206,${0.75 * a})`;
        ctx.shadowBlur = 9;
        ctx.strokeStyle = `rgba(111,224,206,${0.5 + 0.35 * a})`;
        ctx.lineWidth = 1;
        ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
        ctx.restore();

        if (w > 52 && h > 26 && a > 0.7) {
          ctx.fillStyle = `rgba(231,238,241,${0.5 * a})`;
          ctx.font = '400 9.5px "IBM Plex Mono", monospace';
          ctx.fillText(`${p.w}×${p.h}`, x + 6, y + 15);
        }
      });

      if (progress > 0.96) {
        ctx.fillStyle = "#5D717C";
        ctx.font = '500 9.5px "IBM Plex Mono", monospace';
        ctx.textAlign = "right";
        ctx.fillText("REMNANT A · 11.8%", PAD + sw, PAD + sh + 18);
      }
    };

    const start = () => {
      layout();
      if (reduce) {
        draw(1);
        return;
      }
      let t0: number | null = null;
      const frame = (ts: number) => {
        if (t0 === null) t0 = ts;
        const progress = Math.min(1, (ts - t0) / 1900);
        draw(progress);
        if (progress < 1) raf = requestAnimationFrame(frame);
      };
      raf = requestAnimationFrame(frame);
    };

    start();

    let rt: ReturnType<typeof setTimeout>;
    const onResize = () => {
      clearTimeout(rt);
      rt = setTimeout(() => {
        layout();
        draw(1);
      }, 140);
    };
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(rt);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <canvas
      ref={ref}
      width={1200}
      height={620}
      role="img"
      aria-label="2000×1000mm 標準壓克力板排版圖，17 個零件，板材利用率 88.2%"
    />
  );
}
