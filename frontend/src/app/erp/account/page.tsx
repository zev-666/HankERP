"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { api, errorText } from "@/lib/api";

/**
 * 我的帳號／變更密碼（v2.3.8）。每個登入的人都能用，不看角色。
 * 後端 POST /auth/change-password 需要目前的密碼，所以別人拿到你沒登出的電腦也改不了。
 */
export default function AccountPage() {
  const meQ = useQuery({ queryKey: ["me"], queryFn: () => api.getMe() });
  const me = meQ.data?.data;
  const [form, setForm] = useState({ old: "", next: "", again: "" });
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const mut = useMutation({
    mutationFn: () => api.changePassword(form.old, form.next),
    onSuccess: () => { setDone(true); setForm({ old: "", next: "", again: "" }); },
    onError: (e) => setError(errorText(e)),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setDone(false);
    if (!form.old) return setError("請輸入目前的密碼");
    if (form.next.length < 8 || !/\d/.test(form.next)) return setError("新密碼至少 8 個字、要有數字");
    if (form.next !== form.again) return setError("兩次輸入的新密碼不一樣");
    if (form.next === form.old) return setError("新密碼不能跟目前的一樣");
    setError("");
    mut.mutate();
  };

  const inputCls = "w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <div className="p-6 space-y-5 max-w-xl">
      <h1 className="text-xl font-semibold text-slate-800">我的帳號</h1>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <dl className="grid grid-cols-[6rem_1fr] gap-y-2 text-sm">
          <dt className="text-slate-500">姓名</dt><dd className="text-slate-800">{me?.full_name || "—"}</dd>
          <dt className="text-slate-500">登入帳號</dt><dd className="text-slate-800 font-mono text-xs pt-0.5">{me?.email || "—"}</dd>
          <dt className="text-slate-500">角色</dt><dd className="text-slate-800">{me?.role_display_name || "未指定角色"}</dd>
        </dl>
      </div>

      <form onSubmit={submit} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
        <h2 className="font-semibold text-slate-800">變更密碼</h2>
        <div>
          <label htmlFor="pw-old" className="block text-xs text-slate-500 mb-1">目前的密碼</label>
          <input id="pw-old" type="password" autoComplete="current-password" value={form.old}
            onChange={(e) => setForm((f) => ({ ...f, old: e.target.value }))} className={inputCls} />
        </div>
        <div>
          <label htmlFor="pw-new" className="block text-xs text-slate-500 mb-1">新密碼（至少 8 個字、要有數字）</label>
          <input id="pw-new" type="password" autoComplete="new-password" value={form.next}
            onChange={(e) => setForm((f) => ({ ...f, next: e.target.value }))} className={inputCls} />
        </div>
        <div>
          <label htmlFor="pw-again" className="block text-xs text-slate-500 mb-1">再輸入一次新密碼</label>
          <input id="pw-again" type="password" autoComplete="new-password" value={form.again}
            onChange={(e) => setForm((f) => ({ ...f, again: e.target.value }))} className={inputCls} />
        </div>
        {error && <div className="bg-red-50 border border-red-200 text-red-600 rounded-lg p-2.5 text-sm">{error}</div>}
        {done && <div className="bg-green-50 border border-green-200 text-green-700 rounded-lg p-2.5 text-sm">密碼已更新。下次登入請用新密碼。</div>}
        <button type="submit" disabled={mut.isPending}
          className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:bg-blue-300">
          {mut.isPending ? "更新中…" : "更新密碼"}
        </button>
      </form>

      <p className="text-xs text-slate-400">忘記密碼請找系統管理員，在「帳號管理」幫你重設。</p>
    </div>
  );
}
