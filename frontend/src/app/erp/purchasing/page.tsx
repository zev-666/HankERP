"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  draft: { label: "草稿", color: "bg-slate-100 text-slate-500" },
  sent: { label: "已發送", color: "bg-blue-100 text-blue-600" },
  confirmed: { label: "已確認", color: "bg-amber-100 text-amber-600" },
  received: { label: "已收貨", color: "bg-green-100 text-green-600" },
  closed: { label: "已結案", color: "bg-slate-200 text-slate-400" },
};

export default function PurchasingPage() {
  const { data: pos } = useQuery({ queryKey: ["pos"], queryFn: () => api.getPos() });

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">採購管理</h1>
        <button className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ 建立採購單</button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-slate-100 bg-slate-50">
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">採購單號</th>
            <th className="text-right py-3 px-4 text-xs font-medium text-slate-500">總金額</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">預計到貨</th>
            <th className="text-center py-3 px-4 text-xs font-medium text-slate-500">狀態</th>
          </tr></thead>
          <tbody>
            {(pos?.data || []).map((p: any) => {
              const st = STATUS_MAP[p.status] || STATUS_MAP.draft;
              return (
                <tr key={p.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-3 px-4 font-mono text-blue-600 text-xs">{p.po_number}</td>
                  <td className="py-3 px-4 text-right font-semibold">NT$ {p.total_amount?.toLocaleString()}</td>
                  <td className="py-3 px-4 text-slate-500 text-xs">{p.expected_date || "—"}</td>
                  <td className="py-3 px-4 text-center"><span className={`text-xs px-2.5 py-1 rounded-full font-medium ${st.color}`}>{st.label}</span></td>
                </tr>
              );
            })}
            {(!pos?.data || pos.data.length === 0) && (
              <tr><td colSpan={4} className="text-center py-10 text-slate-400">尚無採購單</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
