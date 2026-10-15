import Link from "next/link";
import { BrandMark } from "@/components/brand/BrandMark";

const NAV = [
  { href: "/#process", label: "製造工法" },
  { href: "/portfolio", label: "作品案例" },
  { href: "/#spec", label: "材料規格" },
  { href: "/about", label: "關於我們" },
];

export function SiteHeader() {
  return (
    <nav className="site-nav">
      <div className="site-wrap site-nav-in">
        <Link className="brand" href="/" aria-label="永陛 & 進化 EVEREVO 首頁">
          <BrandMark size={28} />
          <b>
            永陛<i>&amp;</i>進化
          </b>
          <span>EVEREVO</span>
        </Link>
        <div className="site-links">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href}>
              {n.label}
            </Link>
          ))}
        </div>
        <Link className="btn btn-ghost" href="/quote">
          線上詢價
        </Link>
      </div>
    </nav>
  );
}

export function SiteFooter() {
  return (
    <footer className="site-foot">
      <div className="site-wrap site-foot-in">
        <span>
          © {new Date().getFullYear()} 永陛 &amp; 進化 EVEREVO · 永陛實業有限公司 · 新北市樹林區三俊街65巷13號 · 02-2297-3956
        </span>
        <span style={{ display: "flex", gap: 20 }}>
          <Link href="/portfolio">作品案例</Link>
          <Link href="/about">關於我們</Link>
          <Link href="/quote">線上詢價</Link>
        </span>
        <span className="mono" style={{ fontSize: 11, letterSpacing: ".08em" }}>
          ACRYLIC · WOOD · METAL · LED · FINISH
        </span>
      </div>
    </footer>
  );
}
