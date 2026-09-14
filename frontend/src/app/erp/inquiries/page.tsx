"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

const STATUS_LABEL: Record<string, string> = {
  new: "新進",
  contacted: "已聯繫",
  quoted: "已報價",
  won: "成交",
  lost: "未成交",
  spam: "垃圾訊息",
};

const STATUS_STYLE: Record<string, string> = {
  new: "bg-blue-100 text-blue-700",
  contacted: "bg-amber-100 text-amber-700",
  quoted: "bg-violet-100 text-violet-700",
  won: "bg-emerald-100 text-emerald-700",
  lost: "bg-slate-100 text-slate-500",
  spam: "bg-red-50 text-red-500",
};

export default function InquiriesPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<string>("");
  const [selected, setSelected] = useState<any>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["inquiries", filter],
    queryFn: () => api.getInquiries(filter || undefined),
  });

  const statusMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.updateInquiryStatus(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inquiries"] }),
  });

  const convertMut = useMutation({
    mutationFn: (id: string) => api.convertInquiry(id),
    onSuccess: (res: any) => {
      qc.invalidateQueries({ queryKey: ["inquiries"] });
      qc.invalidateQueries({ queryKey: ["customers"] });
      setSelected(null);
      alert(res.message);
    },
  });

  const counts: Record<string, number> = data?.status_counts || {};
  const rows: any[] = data?.data || [];

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">線上詢價</h1>
          <p className="text-xs text-slate-400 mt-1">官網 /quote 表單送出的需求會即時出現在這裡</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setFilter("")}
          className={`px-3 py-1.5 rounded-full text-xs font-medium ${
            filter === "" ? "bg-slate-900 text-white" : "bg-white border border-slate-200 text-slate-600"
          }`}
        >
          全部 {rows.length > 0 && filter === "" ? `(${rows.length})` : ""}
        </button>
        {Object.keys(STATUS_LABEL).map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium ${
              filter === s ? "bg-slate-900 text-white" : "bg-white border border-slate-200 text-slate-600"
            }`}
          >
            {STATUS_LABEL[s]}
            {counts[s] ? ` (${counts[s]})` : ""}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">收到時間</th>
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">聯絡人 / 公司</th>
              <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">需求</th>
              <th className="text-center py-3 px-4 text-xs font-medium text-slate-500">狀態</th>
              <th className="text-right py-3 px-4 text-xs font-medium text-slate-500">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={5} className="py-10 text-center text-slate-400 text-sm">載入中…</td>
              </tr>
            )}
            {!isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={5} className="py-10 text-center text-slate-400 text-sm">
                  目前沒有詢價紀錄
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="py-3 px-4 text-xs text-slate-500 whitespace-nowrap">
                  {r.created_at ? new Date(r.created_at).toLocaleString("zh-TW") : "—"}
                </td>
                <td className="py-3 px-4">
                  <div className="font-medium text-slate-800">{r.name}</div>
                  <div className="text-xs text-slate-400">{r.company || r.email}</div>
                </td>
                <td className="py-3 px-4 text-slate-600">
                  <div>{r.product_type || "—"}</div>
                  <div className="text-xs text-slate-400">{r.quantity || ""}</div>
                </td>
                <td className="py-3 px-4 text-center">
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${STATUS_STYLE[r.status] || ""}`}>
                    {STATUS_LABEL[r.status] || r.status}
                  </span>
                </td>
                <td className="py-3 px-4 text-right">
                  <button
                    onClick={() => setSelected(r)}
                    className="text-blue-600 hover:text-blue-700 text-xs font-medium"
                  >
                    檢視
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50" onClick={() => setSelected(null)}>
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-800">{selected.name}</h2>
                <p className="text-sm text-slate-500">{selected.company || "—"}</p>
              </div>
              <button onClick={() => setSelected(null)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <div><dt className="text-xs text-slate-400">Email</dt><dd className="text-slate-700">{selected.email}</dd></div>
              <div><dt className="text-xs text-slate-400">電話</dt><dd className="text-slate-700">{selected.phone || "—"}</dd></div>
              <div><dt className="text-xs text-slate-400">產品類型</dt><dd className="text-slate-700">{selected.product_type || "—"}</dd></div>
              <div><dt className="text-xs text-slate-400">預計數量</dt><dd className="text-slate-700">{selected.quantity || "—"}</dd></div>
            </dl>

            <div>
              <div className="text-xs text-slate-400 mb-1">需求說明</div>
              <p className="text-sm text-slate-700 bg-slate-50 rounded-lg p-3 whitespace-pre-line">
                {selected.description || "—"}
              </p>
            </div>

            <div>
              <div className="text-xs text-slate-400 mb-1.5">更新狀態</div>
              <div className="flex flex-wrap gap-2">
                {Object.keys(STATUS_LABEL).map((s) => (
                  <button
                    key={s}
                    onClick={() => statusMut.mutate({ id: selected.id, status: s })}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border ${
                      selected.status === s
                        ? "bg-slate-900 text-white border-slate-900"
                        : "border-slate-200 text-slate-600 hover:border-slate-400"
                    }`}
                  >
                    {STATUS_LABEL[s]}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={() => convertMut.mutate(selected.id)}
              disabled={convertMut.isPending}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white py-2.5 rounded-lg text-sm font-medium"
            >
              {selected.converted_customer_id ? "已建立客戶（再次點擊不會重複建立）" : "轉為正式客戶"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
