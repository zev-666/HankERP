"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Package, AlertTriangle, Layers } from "lucide-react";

function Tab({ active, onClick, children }: any) {
  return (
    <button onClick={onClick}
      className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${active ? "border-blue-600 text-blue-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}>
      {children}
    </button>
  );
}

export default function InventoryPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"balance"|"sheets"|"remnants"|"alerts">("balance");
  const [receiveForm, setReceiveForm] = useState({ material_id: "", actual_length_mm: 2000, actual_width_mm: 1000, quantity: 1, batch_no: "" });
  const [showReceive, setShowReceive] = useState(false);

  const { data: balances } = useQuery({ queryKey: ["balances"], queryFn: () => api.getBalances() });
  const { data: sheets } = useQuery({ queryKey: ["sheets"], queryFn: () => api.getSheets(false) });
  const { data: remnants } = useQuery({ queryKey: ["remnants"], queryFn: () => api.getRemnants() });
  const { data: alerts } = useQuery({ queryKey: ["lowstock"], queryFn: () => api.getLowStock() });

  const receiveMut = useMutation({
    mutationFn: (d: any) => api.receiveSheets(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["sheets"] }); qc.invalidateQueries({ queryKey: ["balances"] }); setShowReceive(false); },
  });

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">庫存管理</h1>
        <button onClick={() => setShowReceive(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          + 板材入庫
        </button>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="flex border-b border-slate-200 px-4">
          <Tab active={tab === "balance"} onClick={() => setTab("balance")}>庫存餘額</Tab>
          <Tab active={tab === "sheets"} onClick={() => setTab("sheets")}>板材庫存</Tab>
          <Tab active={tab === "remnants"} onClick={() => setTab("remnants")}>剩料管理</Tab>
          <Tab active={tab === "alerts"} onClick={() => setTab("alerts")}>
            預警 {alerts?.data?.length > 0 && <span className="ml-1 bg-red-500 text-white text-[10px] px-1.5 py-0.5 rounded-full">{alerts.data.length}</span>}
          </Tab>
        </div>
        <div className="p-4">
          {tab === "balance" && (
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-100">
                <th className="text-left py-2 px-3 text-xs text-slate-500">物料ID</th>
                <th className="text-left py-2 px-3 text-xs text-slate-500">倉庫</th>
                <th className="text-right py-2 px-3 text-xs text-slate-500">庫存量</th>
                <th className="text-right py-2 px-3 text-xs text-slate-500">保留量</th>
                <th className="text-right py-2 px-3 text-xs text-slate-500">可用量</th>
              </tr></thead>
              <tbody>
                {(balances?.data || []).map((b: any) => (
                  <tr key={b.id} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="py-2 px-3 font-mono text-xs text-slate-600">{b.material_id.slice(-8)}</td>
                    <td className="py-2 px-3"><span className="bg-slate-100 text-slate-600 text-xs px-2 py-0.5 rounded">{b.warehouse_code}</span></td>
                    <td className="py-2 px-3 text-right">{b.qty_on_hand}</td>
                    <td className="py-2 px-3 text-right text-amber-600">{b.qty_reserved}</td>
                    <td className="py-2 px-3 text-right font-medium text-green-600">{b.qty_available}</td>
                  </tr>
                ))}
                {(!balances?.data || balances.data.length === 0) && <tr><td colSpan={5} className="text-center py-6 text-slate-400 text-sm">無庫存資料</td></tr>}
              </tbody>
            </table>
          )}
          {tab === "sheets" && (
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-100">
                <th className="text-left py-2 px-3 text-xs text-slate-500">批號</th>
                <th className="text-right py-2 px-3 text-xs text-slate-500">長(mm)</th>
                <th className="text-right py-2 px-3 text-xs text-slate-500">寬(mm)</th>
                <th className="text-right py-2 px-3 text-xs text-slate-500">數量</th>
                <th className="text-left py-2 px-3 text-xs text-slate-500">狀態</th>
              </tr></thead>
              <tbody>
                {(sheets?.data || []).map((s: any) => (
                  <tr key={s.id} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="py-2 px-3 font-mono text-xs">{s.batch_no || "—"}</td>
                    <td className="py-2 px-3 text-right">{s.actual_length_mm}</td>
                    <td className="py-2 px-3 text-right">{s.actual_width_mm}</td>
                    <td className="py-2 px-3 text-right font-medium">{s.quantity}</td>
                    <td className="py-2 px-3"><span className="bg-green-100 text-green-600 text-xs px-2 py-0.5 rounded">{s.status}</span></td>
                  </tr>
                ))}
                {(!sheets?.data || sheets.data.length === 0) && <tr><td colSpan={5} className="text-center py-6 text-slate-400 text-sm">無板材庫存</td></tr>}
              </tbody>
            </table>
          )}
          {tab === "remnants" && (
            <table className="w-full text-sm">
              <thead><tr className="border-b border-slate-100">
                <th className="text-right py-2 px-3 text-xs text-slate-500">長(mm)</th>
                <th className="text-right py-2 px-3 text-xs text-slate-500">寬(mm)</th>
                <th className="text-right py-2 px-3 text-xs text-slate-500">面積(才)</th>
                <th className="text-left py-2 px-3 text-xs text-slate-500">等級</th>
                <th className="text-left py-2 px-3 text-xs text-slate-500">狀態</th>
              </tr></thead>
              <tbody>
                {(remnants?.data || []).map((r: any) => (
                  <tr key={r.id} className="border-b border-slate-50 hover:bg-slate-50">
                    <td className="py-2 px-3 text-right">{r.length_mm}</td>
                    <td className="py-2 px-3 text-right">{r.width_mm}</td>
                    <td className="py-2 px-3 text-right font-medium">{(r.length_mm * r.width_mm / 90000).toFixed(1)}</td>
                    <td className="py-2 px-3"><span className={`text-xs px-2 py-0.5 rounded font-medium ${r.grade === "A" ? "bg-green-100 text-green-600" : r.grade === "B" ? "bg-amber-100 text-amber-600" : "bg-red-100 text-red-600"}`}>{r.grade}級</span></td>
                    <td className="py-2 px-3 text-xs text-slate-500">{r.status}</td>
                  </tr>
                ))}
                {(!remnants?.data || remnants.data.length === 0) && <tr><td colSpan={5} className="text-center py-6 text-slate-400 text-sm">無剩料記錄</td></tr>}
              </tbody>
            </table>
          )}
          {tab === "alerts" && (
            <div className="space-y-3">
              {(alerts?.data || []).map((a: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-4 bg-red-50 border border-red-100 rounded-xl">
                  <div className="flex items-center gap-3">
                    <AlertTriangle size={16} className="text-red-500" />
                    <div>
                      <div className="font-medium text-slate-800 text-sm">{a.material_name}</div>
                      <div className="text-xs text-slate-500">現存 {a.on_hand} 片 ／ 安全庫存 {a.min_stock_qty} 片</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-red-600 font-semibold">缺少 {a.shortage} 片</div>
                    <div className="text-xs text-slate-400 mt-0.5">建議立即採購</div>
                  </div>
                </div>
              ))}
              {(!alerts?.data || alerts.data.length === 0) && (
                <div className="text-center py-10 text-slate-400"><Package size={32} className="mx-auto mb-2 opacity-30" />庫存充足，無預警</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Receive Modal */}
      {showReceive && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">壓克力板材入庫</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">物料ID（先從物料主檔查詢）</label>
                <input value={receiveForm.material_id} onChange={e => setReceiveForm(f => ({ ...f, material_id: e.target.value }))}
                  placeholder="UUID" className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-500 mb-1">長度 (mm)</label>
                  <input type="number" value={receiveForm.actual_length_mm}
                    onChange={e => setReceiveForm(f => ({ ...f, actual_length_mm: +e.target.value }))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1">寬度 (mm)</label>
                  <input type="number" value={receiveForm.actual_width_mm}
                    onChange={e => setReceiveForm(f => ({ ...f, actual_width_mm: +e.target.value }))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-500 mb-1">數量（張）</label>
                  <input type="number" value={receiveForm.quantity} min={1}
                    onChange={e => setReceiveForm(f => ({ ...f, quantity: +e.target.value }))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1">批號</label>
                  <input value={receiveForm.batch_no}
                    onChange={e => setReceiveForm(f => ({ ...f, batch_no: e.target.value }))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowReceive(false)} className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg text-sm">取消</button>
              <button onClick={() => receiveMut.mutate(receiveForm)} disabled={receiveMut.isPending}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:bg-blue-300">
                {receiveMut.isPending ? "入庫中..." : "確認入庫"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
