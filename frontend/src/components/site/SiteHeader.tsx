import Link from "next/link";

const NAV = [
  { href: "/portfolio", label: "作品案例" },
  { href: "/#process", label: "製造工法" },
  { href: "/about", label: "關於我們" },
];

export function SiteHeader() {
  return (
    <header className="border-b border-slate-100 sticky top-0 bg-white/95 backdrop-blur z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="font-semibold text-slate-800">
          龜山壓克力製造
        </Link>
        <nav className="flex items-center gap-4 md:gap-8 text-sm text-slate-600">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className="hidden sm:inline hover:text-slate-900">
              {n.label}
            </Link>
          ))}
          <Link
            href="/quote"
            className="bg-slate-900 text-white px-4 py-2 rounded-full hover:bg-slate-700 transition-colors"
          >
            線上詢價
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="border-t border-slate-100 mt-16">
      <div className="max-w-6xl mx-auto px-6 py-10 grid gap-6 md:grid-cols-3 text-sm">
        <div>
          <div className="font-semibold text-slate-800">龜山壓克力製造</div>
          <p className="text-slate-500 mt-2 leading-relaxed">
            桃園龜山 · 20年複合式壓克力展示架製造
          </p>
        </div>
        <div className="text-slate-500 space-y-1.5">
          <Link href="/portfolio" className="block hover:text-slate-800">作品案例</Link>
          <Link href="/about" className="block hover:text-slate-800">關於我們</Link>
          <Link href="/quote" className="block hover:text-slate-800">線上詢價</Link>
        </div>
        <div className="text-slate-400">
          © {new Date().getFullYear()} 龜山壓克力製造 · 桃園市龜山區
        </div>
      </div>
    </footer>
  );
}
