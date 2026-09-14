"use client";
import { useState } from "react";
import Link from "next/link";
import { SiteHeader, SiteFooter } from "@/components/site/SiteHeader";
import { PUBLIC_API_BASE } from "@/lib/publicApi";

const PRODUCT_TYPES = [
  "彩妝展示架",
  "酒類展示櫃",
  "家電展示架",
  "尿布展示架",
  "客製化展示櫃",
];

export default function QuotePage() {
  const [form, setForm] = useState({
    name: "",
    company: "",
    email: "",
    phone: "",
    product_type: PRODUCT_TYPES[0],
    description: "",
    quantity: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * v2.0：真正送出到後端。
   * 先前這裡只有 setSubmitted(true)，畫面會顯示「詢價已送出」，
   * 但沒有任何 API 呼叫——客戶填的需求直接消失，業務端永遠看不到。
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch(`${PUBLIC_API_BASE}/api/v1/public/inquiries`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, source_page: "/quote" }),
      });
      if (res.status === 429) {
        throw new Error("送出次數過於頻繁，請稍後再試，或直接來電與我們聯繫。");
      }
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(
          typeof detail?.detail === "string"
            ? detail.detail
            : "送出失敗，請確認必填欄位後再試一次。",
        );
      }
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "送出失敗，請稍後再試。");
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="bg-slate-50 min-h-screen flex flex-col">
        <SiteHeader />
        <div className="flex-1 flex items-center justify-center px-4 py-20">
          <div className="bg-white rounded-2xl p-10 text-center max-w-md shadow-sm border border-slate-100">
            <div className="text-3xl mb-3">✓</div>
            <h1 className="text-xl font-semibold text-slate-800">詢價已送出</h1>
            <p className="text-slate-500 mt-2 text-sm leading-relaxed">
              我們已收到您的需求，業務人員將於1個工作日內與您聯繫，提供初步報價評估。
            </p>
            <Link
              href="/portfolio"
              className="inline-block mt-6 text-sm text-slate-700 underline underline-offset-4"
            >
              先看看我們的作品案例 →
            </Link>
          </div>
        </div>
        <SiteFooter />
      </div>
    );
  }

  const field = "w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900/10 focus:border-slate-400";
  const label = "block text-xs text-slate-500 mb-1";

  return (
    <div className="bg-slate-50 min-h-screen">
      <SiteHeader />
      <div className="py-14 px-4">
        <div className="max-w-lg mx-auto">
          <h1 className="text-2xl font-semibold text-slate-800 mb-2">線上詢價</h1>
          <p className="text-slate-500 text-sm mb-8">
            請填寫您的需求，我們將提供客製化壓克力展示架報價
          </p>

          <form
            onSubmit={handleSubmit}
            className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4"
          >
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={label}>姓名 *</label>
                <input
                  required
                  maxLength={100}
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className={field}
                />
              </div>
              <div>
                <label className={label}>公司名稱</label>
                <input
                  maxLength={200}
                  value={form.company}
                  onChange={(e) => setForm((f) => ({ ...f, company: e.target.value }))}
                  className={field}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={label}>Email *</label>
                <input
                  required
                  type="email"
                  maxLength={200}
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  className={field}
                />
              </div>
              <div>
                <label className={label}>聯絡電話</label>
                <input
                  maxLength={50}
                  value={form.phone}
                  onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                  className={field}
                />
              </div>
            </div>

            <div>
              <label className={label}>產品類型</label>
              <select
                value={form.product_type}
                onChange={(e) => setForm((f) => ({ ...f, product_type: e.target.value }))}
                className={field}
              >
                {PRODUCT_TYPES.map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </div>

            <div>
              <label className={label}>預計數量</label>
              <input
                maxLength={100}
                value={form.quantity}
                onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))}
                placeholder="例如：100台"
                className={field}
              />
            </div>

            <div>
              <label className={label}>需求說明</label>
              <textarea
                rows={4}
                maxLength={4000}
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                placeholder="請描述尺寸、材質、燈光需求等"
                className={field}
              />
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-slate-900 hover:bg-slate-700 disabled:bg-slate-400 text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
            >
              {submitting ? "送出中…" : "送出詢價"}
            </button>
          </form>
        </div>
      </div>
      <SiteFooter />
    </div>
  );
}
