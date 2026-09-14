"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

const EMPTY = {
  title: "",
  client_name: "",
  industry: "彩妝",
  product_type: "",
  dimensions: "",
  materials: "",
  cover_image_url: "",
  challenge: "",
  solution: "",
  result: "",
  is_featured: false,
};

export default function PortfolioAdminPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ ...EMPTY });

  const { data, isLoading } = useQuery({
    queryKey: ["portfolio-cases"],
    queryFn: () => api.getPortfolioCases(),
  });

  const createMut = useMutation({
    mutationFn: (d: any) => api.createPortfolioCase(d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["portfolio-cases"] });
      setShowCreate(false);
      setForm({ ...EMPTY });
    },
  });

  const publishMut = useMutation({
    mutationFn: (id: string) => api.publishPortfolioCase(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["portfolio-cases"] }),
  });

  const rows: any[] = data?.data || [];
  const field = "w-full border border-slate-300 rounded-lg px-3 py-2 text-sm";
  const label = "block text-xs text-slate-500 mb-1";

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">作品管理</h1>
          <p className="text-xs text-slate-400 mt-1">
            發佈後即時顯示於官網 /portfolio 與首頁「合作案例」
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          + 新增作品
        </button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">標題</th>
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">產業</th>
              <th className="text-center py-3 px-4 text-xs font-medium text-slate-500">精選</th>
              <th className="text-center py-3 px-4 text-xs font-medium text-slate-500">官網狀態</th>
              <th className="text-right py-3 px-4 text-xs font-medium text-slate-500">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={5} className="py-10 text-center text-slate-400 text-sm">載入中…</td></tr>
            )}
            {!isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={5} className="py-10 text-center text-slate-400 text-sm">
                  尚無作品案例。新增並發佈後，官網才會顯示內容。
                </td>
              </tr>
            )}
            {rows.map((c) => (
              <tr key={c.id} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="py-3 px-4 font-medium text-slate-800">{c.title}</td>
                <td className="py-3 px-4 text-slate-600">{c.industry || "—"}</td>
                <td className="py-3 px-4 text-center">{c.is_featured ? "★" : "—"}</td>
                <td className="py-3 px-4 text-center">
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                      c.published ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {c.published ? "已發佈" : "草稿"}
                  </span>
                </td>
                <td className="py-3 px-4 text-right">
                  {c.published ? (
                    <a
                      href={`/portfolio/${c.slug}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-slate-500 hover:text-slate-800 text-xs font-medium"
                    >
                      在官網檢視 ↗
                    </a>
                  ) : (
                    <button
                      onClick={() => publishMut.mutate(c.id)}
                      disabled={publishMut.isPending}
                      className="text-blue-600 hover:text-blue-700 text-xs font-medium"
                    >
                      發佈到官網
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50" onClick={() => setShowCreate(false)}>
          <div
            className="bg-white rounded-2xl p-6 w-full max-w-xl max-h-[85vh] overflow-y-auto space-y-3"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-slate-800">新增作品案例</h2>

            <div><label className={label}>標題 *</label>
              <input className={field} value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} /></div>

            <div className="grid grid-cols-2 gap-3">
              <div><label className={label}>客戶名稱</label>
                <input className={field} value={form.client_name} onChange={(e) => setForm((f) => ({ ...f, client_name: e.target.value }))} /></div>
              <div><label className={label}>產業</label>
                <input className={field} value={form.industry} onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))} /></div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div><label className={label}>產品類型</label>
                <input className={field} value={form.product_type} onChange={(e) => setForm((f) => ({ ...f, product_type: e.target.value }))} /></div>
              <div><label className={label}>尺寸</label>
                <input className={field} placeholder="W450 × D300 × H600 mm" value={form.dimensions} onChange={(e) => setForm((f) => ({ ...f, dimensions: e.target.value }))} /></div>
            </div>

            <div><label className={label}>材質</label>
              <input className={field} placeholder="3mm透明壓克力 + 木作底座 + LED燈條" value={form.materials} onChange={(e) => setForm((f) => ({ ...f, materials: e.target.value }))} /></div>

            <div><label className={label}>封面圖片網址</label>
              <input className={field} placeholder="https://…" value={form.cover_image_url} onChange={(e) => setForm((f) => ({ ...f, cover_image_url: e.target.value }))} /></div>

            <div><label className={label}>客戶挑戰</label>
              <textarea rows={2} className={field} value={form.challenge} onChange={(e) => setForm((f) => ({ ...f, challenge: e.target.value }))} /></div>
            <div><label className={label}>我們的作法</label>
              <textarea rows={2} className={field} value={form.solution} onChange={(e) => setForm((f) => ({ ...f, solution: e.target.value }))} /></div>
            <div><label className={label}>成果</label>
              <textarea rows={2} className={field} value={form.result} onChange={(e) => setForm((f) => ({ ...f, result: e.target.value }))} /></div>

            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input type="checkbox" checked={form.is_featured} onChange={(e) => setForm((f) => ({ ...f, is_featured: e.target.checked }))} />
              設為精選案例
            </label>

            <div className="flex gap-3 pt-2">
              <button onClick={() => setShowCreate(false)} className="flex-1 border border-slate-300 py-2.5 rounded-lg text-sm">取消</button>
              <button
                onClick={() => createMut.mutate(form)}
                disabled={!form.title || createMut.isPending}
                className="flex-1 bg-blue-600 disabled:bg-slate-300 text-white py-2.5 rounded-lg text-sm font-medium"
              >
                {createMut.isPending ? "建立中…" : "建立（草稿）"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
