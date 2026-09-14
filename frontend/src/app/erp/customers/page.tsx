"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export default function CustomersPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", industry: "彩妝", contact_name: "", contact_email: "", contact_phone: "" });

  const { data: customers } = useQuery({ queryKey: ["customers"], queryFn: () => api.getCustomers() });
  const createMut = useMutation({
    mutationFn: (d: any) => api.createCustomer(d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["customers"] }); setShowCreate(false); },
  });

  const tierColor: Record<string, string> = { vip: "bg-amber-100 text-amber-700", preferred: "bg-blue-100 text-blue-600", standard: "bg-slate-100 text-slate-500" };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-800">客戶管理</h1>
        <button onClick={() => setShowCreate(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">+ 新增客戶</button>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-slate-100 bg-slate-50">
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">編號</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">公司名稱</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">產業</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">聯絡信箱</th>
            <th className="text-center py-3 px-4 text-xs font-medium text-slate-500">等級</th>
          </tr></thead>
          <tbody>
            {(customers?.data || []).map((c: any) => (
              <tr key={c.id} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="py-3 px-4 font-mono text-xs text-slate-500">{c.code || "—"}</td>
                <td className="py-3 px-4 font-medium text-slate-800">{c.name}</td>
                <td className="py-3 px-4 text-slate-600">{c.industry || "—"}</td>
                <td className="py-3 px-4 text-slate-500 text-xs">{c.contact_email || "—"}</td>
                <td className="py-3 px-4 text-center"><span className={`text-xs px-2.5 py-1 rounded-full font-medium ${tierColor[c.tier] || tierColor.standard}`}>{c.tier || "standard"}</span></td>
              </tr>
            ))}
            {(!customers?.data || customers.data.length === 0) && (
              <tr><td colSpan={5} className="text-center py-10 text-slate-400">尚無客戶資料</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold mb-4">新增客戶</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">公司名稱</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">產業類別</label>
                <select value={form.industry} onChange={e => setForm(f => ({ ...f, industry: e.target.value }))} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                  <option>彩妝</option><option>家電</option><option>酒類</option><option>嬰幼用品</option><option>其他</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">聯絡人</label>
                <input value={form.contact_name} onChange={e => setForm(f => ({ ...f, contact_name: e.target.value }))} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-500 mb-1">Email</label>
                  <input value={form.contact_email} onChange={e => setForm(f => ({ ...f, contact_email: e.target.value }))} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1">電話</label>
                  <input value={form.contact_phone} onChange={e => setForm(f => ({ ...f, contact_phone: e.target.value }))} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowCreate(false)} className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg text-sm">取消</button>
              <button onClick={() => createMut.mutate(form)} disabled={createMut.isPending || !form.name} className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:bg-blue-300">
                {createMut.isPending ? "建立中..." : "確認新增"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
