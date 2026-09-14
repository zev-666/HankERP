"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Plus, Sparkles } from "lucide-react";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  draft: { label: "草稿", color: "bg-slate-100 text-slate-500" },
  sent: { label: "已送出", color: "bg-blue-100 text-blue-600" },
  accepted: { label: "已成交", color: "bg-green-100 text-green-600" },
  rejected: { label: "已拒絕", color: "bg-red-100 text-red-600" },
  expired: { label: "已過期", color: "bg-slate-200 text-slate-400" },
};

export default function QuotationsPage() {
  const qc = useQueryClient();
  const [showAI, setShowAI] = useState(false);
  const [aiForm, setAiForm] = useState({
    description: "彩妝展示架", quantity: 1,
    acrylic: [{ color: "transparent", thickness_mm: 3, length_mm: 500, width_mm: 400, qty: 2 }],
    cnc_minutes: 30, assembly_hours: 1,
  });
  const [aiResult, setAiResult] = useState<any>(null);

  const { data: quotes } = useQuery({ queryKey: ["quotes"], queryFn: () => api.getQuotations() });

  const estimateMut = useMutation({
    mutationFn: () => api.aiEstimate({
      product_description: aiForm.description,
      acrylic_items: aiForm.acrylic,
      operations: [
        { type: "cnc_cut", estimated_minutes: aiForm.cnc_minutes },
        { type: "assembly", estimated_minutes: aiForm.assembly_hours * 60 },
      ],
      quantity: aiForm.quantity,
    }),
    onSuccess: (data) => setAiResult(data.estimate),
  });

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">報價管理</h1>
        <button onClick={() => setShowAI(true)}
          className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:opacity-90">
          <Sparkles size={14} /> AI快速估價
        </button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-slate-100 bg-slate-50">
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">報價單號</th>
            <th className="text-right py-3 px-4 text-xs font-medium text-slate-500">報價金額</th>
            <th className="text-center py-3 px-4 text-xs font-medium text-slate-500">狀態</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">建立日期</th>
          </tr></thead>
          <tbody>
            {(quotes?.data || []).map((q: any) => {
              const st = STATUS_MAP[q.status] || STATUS_MAP.draft;
              return (
                <tr key={q.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-3 px-4 font-mono text-blue-600 text-xs">{q.quote_number}</td>
                  <td className="py-3 px-4 text-right font-semibold">NT$ {q.final_price?.toLocaleString()}</td>
                  <td className="py-3 px-4 text-center"><span className={`text-xs px-2.5 py-1 rounded-full font-medium ${st.color}`}>{st.label}</span></td>
                  <td className="py-3 px-4 text-slate-500 text-xs">{new Date(q.created_at).toLocaleDateString("zh-TW")}</td>
                </tr>
              );
            })}
            {(!quotes?.data || quotes.data.length === 0) && (
              <tr><td colSpan={4} className="text-center py-10 text-slate-400">尚無報價單</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showAI && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold mb-1 flex items-center gap-2"><Sparkles size={16} className="text-purple-600" /> AI快速估價</h2>
            <p className="text-xs text-slate-400 mb-4">輸入規格，系統自動依壓克力單價表與工序成本計算報價</p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">產品說明</label>
                <input value={aiForm.description} onChange={e => setAiForm(f => ({ ...f, description: e.target.value }))}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="border border-slate-200 rounded-lg p-3">
                <div className="text-xs font-medium text-slate-600 mb-2">壓克力板材</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-slate-400">顏色</label>
                    <select value={aiForm.acrylic[0].color}
                      onChange={e => setAiForm(f => ({ ...f, acrylic: [{ ...f.acrylic[0], color: e.target.value }] }))}
                      className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs">
                      <option value="transparent">透明</option>
                      <option value="white">白色</option>
                      <option value="black">黑色</option>
                      <option value="frosted">霧面</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">厚度(mm)</label>
                    <select value={aiForm.acrylic[0].thickness_mm}
                      onChange={e => setAiForm(f => ({ ...f, acrylic: [{ ...f.acrylic[0], thickness_mm: +e.target.value }] }))}
                      className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs">
                      {[2,3,5,8,10].map(t => <option key={t} value={t}>{t}mm</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">長 × 寬 (mm)</label>
                    <div className="flex gap-1">
                      <input type="number" value={aiForm.acrylic[0].length_mm}
                        onChange={e => setAiForm(f => ({ ...f, acrylic: [{ ...f.acrylic[0], length_mm: +e.target.value }] }))}
                        className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs" />
                      <input type="number" value={aiForm.acrylic[0].width_mm}
                        onChange={e => setAiForm(f => ({ ...f, acrylic: [{ ...f.acrylic[0], width_mm: +e.target.value }] }))}
                        className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs" />
                    </div>
                  </div>
                  <div>
                    <label className="text-[10px] text-slate-400">片數</label>
                    <input type="number" value={aiForm.acrylic[0].qty}
                      onChange={e => setAiForm(f => ({ ...f, acrylic: [{ ...f.acrylic[0], qty: +e.target.value }] }))}
                      className="w-full border border-slate-200 rounded px-2 py-1.5 text-xs" />
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-xs text-slate-500 mb-1">CNC工時(分)</label>
                  <input type="number" value={aiForm.cnc_minutes}
                    onChange={e => setAiForm(f => ({ ...f, cnc_minutes: +e.target.value }))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1">組裝工時(時)</label>
                  <input type="number" value={aiForm.assembly_hours}
                    onChange={e => setAiForm(f => ({ ...f, assembly_hours: +e.target.value }))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1">生產數量</label>
                  <input type="number" value={aiForm.quantity}
                    onChange={e => setAiForm(f => ({ ...f, quantity: +e.target.value }))}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
            </div>

            {aiResult && (
              <div className="mt-4 bg-purple-50 rounded-xl p-4 space-y-1.5 text-sm">
                <div className="flex justify-between"><span className="text-slate-500">材料成本</span><span>NT$ {aiResult.material_cost?.toLocaleString()}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">加工成本</span><span>NT$ {aiResult.processing_cost?.toLocaleString()}</span></div>
                <div className="flex justify-between font-semibold text-purple-700 border-t border-purple-200 pt-1.5 mt-1.5">
                  <span>建議報價（總額）</span><span>NT$ {aiResult.final_price?.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-xs text-slate-400"><span>單價</span><span>NT$ {aiResult.unit_price?.toLocaleString()}</span></div>
              </div>
            )}

            <div className="flex gap-3 mt-5">
              <button onClick={() => { setShowAI(false); setAiResult(null); }} className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg text-sm">關閉</button>
              <button onClick={() => estimateMut.mutate()} disabled={estimateMut.isPending}
                className="flex-1 bg-purple-600 text-white py-2 rounded-lg text-sm hover:bg-purple-700 disabled:bg-purple-300">
                {estimateMut.isPending ? "計算中..." : "計算報價"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
