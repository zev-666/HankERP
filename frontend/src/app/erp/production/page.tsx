"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Play, CheckCircle, ClipboardList, PackageMinus } from "lucide-react";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  draft: { label: "草稿", color: "bg-slate-100 text-slate-500" },
  released: { label: "已發佈", color: "bg-blue-100 text-blue-600" },
  in_progress: { label: "進行中", color: "bg-amber-100 text-amber-600" },
  completed: { label: "已完成", color: "bg-green-100 text-green-600" },
  closed: { label: "已關閉", color: "bg-slate-200 text-slate-400" },
};

export default function ProductionPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ product_id: "", quantity: 1, priority: 5, planned_start: "", planned_end: "" });

  const { data: wos } = useQuery({
    queryKey: ["wos", statusFilter],
    queryFn: () => api.getWos(statusFilter || undefined),
  });

  const createMut = useMutation({
    mutationFn: (d: any) => api.createWo(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["wos"] }); setShowCreate(false); },
  });
  const releaseMut = useMutation({
    mutationFn: (id: string) => api.releaseWo(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["wos"] }),
  });

  // v2.0：發料與完工入庫。這兩步先前只存在於規格書，
  // 現場領了料、做完了工，庫存數字都不會動。
  const refreshAll = () => {
    qc.invalidateQueries({ queryKey: ["wos"] });
    qc.invalidateQueries({ queryKey: ["balances"] });
  };
  const issueMut = useMutation({
    mutationFn: (id: string) => api.issueWoMaterials(id),
    onSuccess: (res: any) => { refreshAll(); alert(res.message); },
    onError: (err: any) => {
      // 庫存不足時後端回409並附缺料清單，直接攤開給倉管看，不要只丟一句「失敗」
      let msg = err?.message || "發料失敗";
      try {
        const parsed = JSON.parse(msg);
        if (parsed?.shortages) {
          msg = `${parsed.message}\n\n` + parsed.shortages
            .map((s: any) => `· 料號 ${String(s.material_id).slice(-8)}：需 ${s.required_qty}，現有 ${s.on_hand_qty}，缺 ${s.shortage_qty}`)
            .join("\n");
        }
      } catch { /* 非JSON訊息就原樣顯示 */ }
      alert(msg);
    },
  });
  const completeMut = useMutation({
    mutationFn: (id: string) => api.completeWo(id),
    onSuccess: (res: any) => { refreshAll(); alert(res.message); },
    onError: (err: any) => alert(err?.message || "完工入庫失敗"),
  });

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">生產工單管理</h1>
        <button onClick={() => setShowCreate(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          + 建立工單
        </button>
      </div>

      {/* Status Filter */}
      <div className="flex gap-2">
        {["", "draft", "released", "in_progress", "completed"].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${statusFilter === s ? "bg-blue-600 text-white" : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"}`}>
            {s === "" ? "全部" : STATUS_MAP[s]?.label}
          </button>
        ))}
      </div>

      {/* Work Orders Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-slate-100 bg-slate-50">
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">工單編號</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">產品</th>
            <th className="text-right py-3 px-4 text-xs font-medium text-slate-500">數量</th>
            <th className="text-center py-3 px-4 text-xs font-medium text-slate-500">優先度</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">預計完工</th>
            <th className="text-center py-3 px-4 text-xs font-medium text-slate-500">狀態</th>
            <th className="text-center py-3 px-4 text-xs font-medium text-slate-500">操作</th>
          </tr></thead>
          <tbody>
            {(wos?.data || []).map((wo: any) => {
              const st = STATUS_MAP[wo.status] || STATUS_MAP.draft;
              return (
                <tr key={wo.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-3 px-4 font-mono text-blue-600 text-xs">{wo.wo_number}</td>
                  <td className="py-3 px-4 text-slate-600 text-xs font-mono">{wo.product_id?.slice(-8)}</td>
                  <td className="py-3 px-4 text-right font-medium">{wo.quantity} 台</td>
                  <td className="py-3 px-4 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${wo.priority <= 3 ? "bg-red-100 text-red-600" : wo.priority <= 6 ? "bg-amber-100 text-amber-600" : "bg-slate-100 text-slate-500"}`}>P{wo.priority}</span>
                  </td>
                  <td className="py-3 px-4 text-slate-500 text-xs">{wo.planned_end || "—"}</td>
                  <td className="py-3 px-4 text-center">
                    <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${st.color}`}>{st.label}</span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <div className="flex items-center justify-center gap-3">
                      {wo.status === "draft" && (
                        <button onClick={() => releaseMut.mutate(wo.id)}
                          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700">
                          <Play size={11} /> 發佈
                        </button>
                      )}
                      {(wo.status === "released" || wo.status === "in_progress") && (
                        <button onClick={() => issueMut.mutate(wo.id)} disabled={issueMut.isPending}
                          className="flex items-center gap-1 text-xs text-amber-600 hover:text-amber-700 disabled:text-slate-300">
                          <PackageMinus size={11} /> 發料
                        </button>
                      )}
                      {wo.status === "in_progress" && (
                        <button onClick={() => completeMut.mutate(wo.id)} disabled={completeMut.isPending}
                          className="flex items-center gap-1 text-xs text-green-600 hover:text-green-700 disabled:text-slate-300">
                          <CheckCircle size={11} /> 完工入庫
                        </button>
                      )}
                      {wo.status === "completed" && (
                        <span className="text-xs text-slate-400">已入庫</span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {(!wos?.data || wos.data.length === 0) && (
              <tr><td colSpan={7} className="text-center py-10 text-slate-400">
                <ClipboardList size={28} className="mx-auto mb-2 opacity-30" />
                無工單記錄
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">建立生產工單</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">產品ID</label>
                <input value={form.product_id} onChange={e => setForm(f => ({ ...f, product_id: e.target.value }))}
                  placeholder="產品UUID" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-500 mb-1">生產數量（台）</label>
                  <input type="number" value={form.quantity} min={1}
                    onChange={e => setForm(f => ({ ...f, quantity: +e.target.value }))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1">優先度（1最高）</label>
                  <input type="number" value={form.priority} min={1} max={10}
                    onChange={e => setForm(f => ({ ...f, priority: +e.target.value }))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-500 mb-1">計劃開始日</label>
                  <input type="date" value={form.planned_start}
                    onChange={e => setForm(f => ({ ...f, planned_start: e.target.value }))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1">計劃完工日</label>
                  <input type="date" value={form.planned_end}
                    onChange={e => setForm(f => ({ ...f, planned_end: e.target.value }))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowCreate(false)} className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg text-sm">取消</button>
              <button onClick={() => createMut.mutate(form)} disabled={createMut.isPending || !form.product_id}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:bg-blue-300">
                {createMut.isPending ? "建立中..." : "建立工單"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
