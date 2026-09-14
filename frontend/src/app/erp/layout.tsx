"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { Sidebar } from "@/components/erp/Sidebar";

export default function ErpLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();
  // v2.0：補上依賴陣列。原本的空陣列在 React 18 StrictMode 與未來的並行渲染下，
  // 有機會拿到過期的 isAuthenticated 閉包，導致登入狀態改變時沒有重新導向。
  useEffect(() => {
    if (!isAuthenticated()) router.replace("/login");
  }, [isAuthenticated, router]);
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
