"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { ScanLine, ClipboardList, LogOut } from "lucide-react";

export default function MesHomePage() {
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const [woInput, setWoInput] = useState("");

  const { data: wos } = useQuery({
    queryKey: ["mes-wos"],
    queryFn: () => api.getWos("released"),
    refetchInterval: 15000,
  });
  const { data: inProgress } = useQuery({
    queryKey: ["mes-wos-active"],
    queryFn: () => api.getWos("in_progress"),
    refetchInterval: 15000,
  });

  const handleScan = (e: React.FormEvent) => {
    e.preventDefault();
    if (woInput.trim()) {
      router.push(`/mes/workorder/${woInput.trim()}`);
    }
  };

  const allActive = [...(inProgress?.data || []), ...(wos?.data || [])];

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top bar — large, simple */}
      <div className="bg-slate-900 text-white px-6 py-5 flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold">現場報工系統</div>
          <div className="text-slate-400 text-sm">{user?.full_name}</div>
        </div>
        <button onClick={logout} className="flex items-center gap-2 text-slate-300 text-sm">
          <LogOut size={18} /> 登出
        </button>
      </div>

      {/* Scan input — big and obvious */}
      <div className="p-6">
        <form onSubmit={handleScan} className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <label className="flex items-center gap-2 text-slate-500 text-sm mb-3">
            <ScanLine size={18} /> 掃描或輸入工單編號
          </label>
          <div className="flex gap-3">
            <input
              autoFocus
              value={woInput}
              onChange={e => setWoInput(e.target.value)}
              placeholder="WO2026-0001"
              className="flex-1 border-2 border-slate-300 rounded-xl px-5 py-4 text-2xl font-mono focus:outline-none focus:border-blue-500"
            />
            <button type="submit" className="bg-blue-600 text-white px-8 rounded-xl text-lg font-medium hover:bg-blue-700">
              開始
            </button>
          </div>
        </form>
      </div>

      {/* Active work order list — big tap targets */}
      <div className="flex-1 px-6 pb-6">
        <div className="flex items-center gap-2 text-slate-600 mb-3">
          <ClipboardList size={18} />
          <span className="font-medium">待處理工單</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {allActive.map((wo: any) => (
            <button
              key={wo.id}
              onClick={() => router.push(`/mes/workorder/${wo.id}`)}
              className="bg-white rounded-2xl border-2 border-slate-200 hover:border-blue-400 p-6 text-left transition-colors active:scale-[0.98]"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xl font-semibold text-slate-800">{wo.wo_number}</span>
                <span className={`text-sm px-3 py-1 rounded-full font-medium ${
                  wo.status === "in_progress" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"
                }`}>
                  {wo.status === "in_progress" ? "進行中" : "待開始"}
                </span>
              </div>
              <div className="text-slate-500 mt-2 text-lg">{wo.quantity} 台</div>
            </button>
          ))}
          {allActive.length === 0 && (
            <div className="col-span-2 text-center py-16 text-slate-400 text-lg">
              目前沒有待處理工單
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
