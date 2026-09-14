"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import {
  LayoutDashboard, Users, FileText, Package, ShoppingCart,
  ClipboardList, Scissors, BarChart3, Settings, LogOut, Wrench, Layers,
  Inbox, Image as ImageIcon
} from "lucide-react";

const NAV = [
  { label: "儀表板", href: "/erp/dashboard", icon: LayoutDashboard },
  { type: "section", label: "業務" },
  { label: "線上詢價", href: "/erp/inquiries", icon: Inbox },
  { label: "客戶管理", href: "/erp/customers", icon: Users },
  { label: "報價管理", href: "/erp/quotations", icon: FileText },
  { type: "section", label: "生產管理" },
  { label: "產品/BOM", href: "/erp/products", icon: Layers },
  { label: "庫存管理", href: "/erp/inventory", icon: Package },
  { label: "採購管理", href: "/erp/purchasing", icon: ShoppingCart },
  { label: "生產工單", href: "/erp/production", icon: ClipboardList },
  { label: "裁切排版", href: "/erp/nesting", icon: Scissors },
  { type: "section", label: "分析" },
  { label: "成本分析", href: "/erp/analytics", icon: BarChart3 },
  { label: "設備管理", href: "/erp/equipment", icon: Wrench },
  { type: "section", label: "官網" },
  { label: "作品管理", href: "/erp/portfolio", icon: ImageIcon },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  return (
    <aside className="w-56 min-h-screen bg-slate-900 flex flex-col shrink-0">
      <div className="p-4 border-b border-slate-700">
        <div className="text-white font-semibold text-sm">龜山壓克力</div>
        <div className="text-slate-400 text-xs mt-0.5">智慧工廠 ERP</div>
      </div>
      <nav className="flex-1 py-2 overflow-y-auto">
        {NAV.map((item, i) => {
          if ("type" in item && item.type === "section") {
            return (
              <div key={i} className="px-4 py-1.5 text-slate-500 text-[10px] uppercase tracking-wider mt-2">
                {item.label}
              </div>
            );
          }
          const Icon = (item as any).icon;
          const active = pathname === item.href;
          return (
            <Link key={item.href} href={item.href!}
              className={`flex items-center gap-2.5 px-4 py-2 text-sm transition-colors ${
                active
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              <Icon size={16} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-4 border-t border-slate-700">
        <div className="text-slate-400 text-xs mb-2">{user?.full_name}</div>
        <button
          onClick={logout}
          className="flex items-center gap-2 text-slate-400 hover:text-white text-xs transition-colors"
        >
          <LogOut size={13} /> 登出
        </button>
      </div>
    </aside>
  );
}
