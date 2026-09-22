"use client";
import { useState } from "react";
import Link from "next/link";
import { SiteHeader, SiteFooter } from "@/components/site/SiteHeader";
import { PUBLIC_API_BASE } from "@/lib/publicApi";

const PRODUCT_TYPES = ["彩妝展示架", "酒類展示櫃", "家電展示架", "尿布展示架", "客製化展示櫃"];

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

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  /** 真正送出到後端 —— v2.0 之前這裡只切換畫面、不呼叫 API，客戶的需求會直接消失 */
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
      if (res.status === 429) throw new Error("送出次數過於頻繁，請稍後再試，或直接來電與我們聯繫。");
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(typeof detail?.detail === "string" ? detail.detail : "送出失敗，請確認必填欄位後再試一次。");
      }
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "送出失敗，請稍後再試。");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <SiteHeader />
      <section className="site-wrap site-sec" style={{ maxWidth: 760 }}>
        {submitted ? (
          <div className="panel cta">
            <div className="eyebrow">Received</div>
            <h1 className="site-h2" style={{ fontSize: "clamp(24px,3.6vw,34px)" }}>
              詢價已送出
            </h1>
            <p>我們已收到您的需求，業務人員將於一個工作日內與您聯繫，提供初步報價評估。</p>
            <Link className="btn btn-ghost" href="/portfolio">
              先看看作品案例 →
            </Link>
          </div>
        ) : (
          <>
            <div className="sec-head">
              <div className="eyebrow">Request a Quote</div>
              <h1 className="site-h2">線上詢價</h1>
              <p className="site-lede">
                把尺寸、材質、數量給我們。圖面還沒定案也可以先談，我們會告訴你哪些做法比較省。
              </p>
            </div>

            <form onSubmit={handleSubmit} className="panel" style={{ padding: "clamp(22px,4vw,34px)", display: "grid", gap: 18 }}>
              <div className="field-row">
                <div className="field">
                  <label htmlFor="q-name">姓名 *</label>
                  <input id="q-name" required maxLength={100} value={form.name} onChange={set("name")} />
                </div>
                <div className="field">
                  <label htmlFor="q-company">公司名稱</label>
                  <input id="q-company" maxLength={200} value={form.company} onChange={set("company")} />
                </div>
              </div>
              <div className="field-row">
                <div className="field">
                  <label htmlFor="q-email">EMAIL *</label>
                  <input id="q-email" required type="email" maxLength={200} value={form.email} onChange={set("email")} />
                </div>
                <div className="field">
                  <label htmlFor="q-phone">聯絡電話</label>
                  <input id="q-phone" maxLength={50} value={form.phone} onChange={set("phone")} />
                </div>
              </div>
              <div className="field-row">
                <div className="field">
                  <label htmlFor="q-type">產品類型</label>
                  <select id="q-type" value={form.product_type} onChange={set("product_type")}>
                    {PRODUCT_TYPES.map((t) => (
                      <option key={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="q-qty">預計數量</label>
                  <input id="q-qty" maxLength={100} placeholder="例如：100 台" value={form.quantity} onChange={set("quantity")} />
                </div>
              </div>
              <div className="field">
                <label htmlFor="q-desc">需求說明</label>
                <textarea
                  id="q-desc"
                  rows={5}
                  maxLength={4000}
                  placeholder="尺寸、材質、燈光需求、品牌雷雕等"
                  value={form.description}
                  onChange={set("description")}
                />
              </div>
              {error && <div className="alert">{error}</div>}
              <div>
                <button type="submit" disabled={submitting} className="btn btn-led">
                  {submitting ? "送出中…" : "送出詢價 →"}
                </button>
              </div>
            </form>
          </>
        )}
      </section>
      <SiteFooter />
    </>
  );
}
