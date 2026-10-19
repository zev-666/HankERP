"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { BrandMark } from "@/components/brand/BrandMark";
import {
  LayoutDashboard, Users, FileText, Package, ShoppingCart,
  ClipboardList, Scissors, BarChart3, Settings, LogOut, Wrench, Layers,
  Inbox, Image as ImageIcon, UserCog, KeyRound
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

// v2.3.8：只有系統管理員看得到「帳號管理」。這只是介面上的整理，
// 真正的權限由後端 PERMISSION_MAP 把關（非管理員打 /auth/users 一律 403）。
const ADMIN_NAV = [
  { type: "section", label: "系統" },
  { label: "帳號管理", href: "/erp/users", icon: UserCog },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  return (
    <aside className="w-56 min-h-screen bg-slate-900 flex flex-col shrink-0">
      <div className="p-4 border-b border-slate-700">
        <div className="flex items-center gap-2.5">
          <BrandMark size={28} />
          <div>
            <div className="text-white font-semibold text-sm tracking-wider">永陛 &amp; 進化</div>
            <div className="text-slate-400 text-[10px] mt-0.5 tracking-[0.3em]">EVEREVO ERP</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 py-2 overflow-y-auto">
        {[...NAV, ...(user?.role === "admin" ? ADMIN_NAV : [])].map((item, i) => {
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
        <Link href="/erp/account"
          className={`flex items-center gap-2 text-xs mb-2 transition-colors ${pathname === "/erp/account" ? "text-white" : "text-slate-400 hover:text-white"}`}>
          <KeyRound size={13} /> 變更密碼
        </Link>
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
