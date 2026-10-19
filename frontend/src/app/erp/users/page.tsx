"use client";
import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, errorText, type AccountUser } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { UserPlus, KeyRound, Pencil, Power, Copy, Check } from "lucide-react";

/**
 * 帳號管理（v2.3.8，僅限系統管理員）。
 * 權限由後端把關（/auth/users 等端點只給 admin），這頁只是操作介面；
 * 非管理員打開會看到後端回的 403 訊息。
 *
 * 員工離職用「停用」不用刪除：帳號留著，歷史單據還查得到是誰做的。
 */

// 隨機初始密碼：避開容易看錯的 0/O、1/l/I，保證含數字（後端要求至少 8 字、含數字）
function generatePassword(): string {
  const letters = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ";
  const digits = "23456789";
  const all = letters + digits;
  const buf = new Uint32Array(10);
  crypto.getRandomValues(buf);
  const chars = Array.from(buf, (n) => all[n % all.length]);
  chars[buf[0] % 8 + 1] = digits[buf[1] % digits.length];
  return chars.join("");
}

function formatTime(iso: string | null): string {
  if (!iso) return "從未登入";
  const d = new Date(iso);
  return d.toLocaleString("zh-TW", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
}

type Modal =
  | { kind: "create" }
  | { kind: "edit"; user: AccountUser }
  | { kind: "reset"; user: AccountUser }
  | null;

export default function UsersPage() {
  const qc = useQueryClient();
  const me = useAuthStore((s) => s.user);
  const [modal, setModal] = useState<Modal>(null);
  const [notice, setNotice] = useState<{ text: string; password?: string } | null>(null);
  const [confirmOff, setConfirmOff] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);

  const usersQ = useQuery({ queryKey: ["users"], queryFn: () => api.getUsers(), retry: false });
  const rolesQ = useQuery({ queryKey: ["roles"], queryFn: () => api.getRoles(), retry: false });
  const roles = rolesQ.data?.data ?? [];
  const users = useMemo(() => usersQ.data?.data ?? [], [usersQ.data]);
  const visible = showInactive ? users : users.filter((u) => u.is_active);
  const inactiveCount = users.filter((u) => !u.is_active).length;

  const toggleMut = useMutation({
    mutationFn: (u: AccountUser) => api.updateUser(u.id, { is_active: !u.is_active }),
    onSuccess: (_d, u) => {
      setConfirmOff(null);
      setNotice({ text: u.is_active ? `已停用「${u.full_name || u.email}」，對方會立刻被登出` : `已重新啟用「${u.full_name || u.email}」` });
      qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (e) => { setConfirmOff(null); setNotice({ text: `操作失敗：${errorText(e)}` }); },
  });

  if (usersQ.isError) {
    return (
      <div className="p-6 space-y-4">
        <h1 className="text-xl font-semibold text-slate-800">帳號管理</h1>
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-4 text-sm">
          {errorText(usersQ.error)}
          <div className="text-amber-700 mt-1">只有「系統管理員」可以管理帳號。要改自己的密碼，請到左下角的「變更密碼」。</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">帳號管理</h1>
          <p className="text-xs text-slate-500 mt-1">每位員工用自己的帳號登入，系統會依角色只顯示他能用的功能。離職請「停用」，資料會保留。</p>
        </div>
        <button onClick={() => setModal({ kind: "create" })}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700">
          <UserPlus size={15} /> 新增帳號
        </button>
      </div>

      {notice && <NoticeBar notice={notice} onClose={() => setNotice(null)} />}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
        <table className="w-full text-sm min-w-[880px]">
          <thead><tr className="border-b border-slate-100 bg-slate-50">
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">姓名</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">登入帳號（Email）</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">角色</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">狀態</th>
            <th className="text-left py-3 px-4 text-xs font-medium text-slate-500">最後登入</th>
            <th className="text-right py-3 px-4 text-xs font-medium text-slate-500">操作</th>
          </tr></thead>
          <tbody>
            {visible.map((u) => {
              const isMe = u.id === me?.id;
              return (
                <tr key={u.id} className={`border-b border-slate-50 ${u.is_active ? "hover:bg-slate-50" : "bg-slate-50/60 text-slate-400"}`}>
                  <td className="py-3 px-4 font-medium text-slate-800">
                    {u.full_name || "—"}{isMe && <span className="ml-1.5 text-xs text-blue-600 font-normal">（你）</span>}
                  </td>
                  <td className="py-3 px-4 text-slate-500 text-xs break-all">{u.email}</td>
                  <td className="py-3 px-4">
                    <span className={`whitespace-nowrap text-xs px-2.5 py-1 rounded-full font-medium ${u.role_name === "admin" ? "bg-purple-100 text-purple-700" : "bg-slate-100 text-slate-600"}`}>
                      {u.role_display_name || "未指定角色"}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    {u.is_active
                      ? <span className="whitespace-nowrap text-xs px-2.5 py-1 rounded-full bg-green-100 text-green-700 font-medium">啟用中</span>
                      : <span className="whitespace-nowrap text-xs px-2.5 py-1 rounded-full bg-slate-200 text-slate-500 font-medium">已停用</span>}
                  </td>
                  <td className="py-3 px-4 text-xs text-slate-500 tabular-nums whitespace-nowrap">{formatTime(u.last_login)}</td>
                  <td className="py-3 px-4">
                    <div className="flex justify-end gap-1.5">
                      <IconButton label="編輯" onClick={() => setModal({ kind: "edit", user: u })}><Pencil size={14} /></IconButton>
                      {!isMe && (
                        <IconButton label="重設密碼" onClick={() => setModal({ kind: "reset", user: u })}><KeyRound size={14} /></IconButton>
                      )}
                      {!isMe && (confirmOff === u.id ? (
                        <span className="flex items-center gap-1">
                          <button onClick={() => toggleMut.mutate(u)} disabled={toggleMut.isPending}
                            className="whitespace-nowrap text-xs px-2.5 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700">確定停用</button>
                          <button onClick={() => setConfirmOff(null)} className="whitespace-nowrap text-xs px-2.5 py-1.5 rounded-lg border border-slate-300 text-slate-600">取消</button>
                        </span>
                      ) : (
                        <IconButton label={u.is_active ? "停用" : "重新啟用"}
                          onClick={() => (u.is_active ? setConfirmOff(u.id) : toggleMut.mutate(u))}>
                          <Power size={14} className={u.is_active ? "text-red-500" : "text-green-600"} />
                        </IconButton>
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}
            {usersQ.isLoading && <tr><td colSpan={6} className="text-center py-10 text-slate-400">載入中…</td></tr>}
            {!usersQ.isLoading && visible.length === 0 && (
              <tr><td colSpan={6} className="text-center py-10 text-slate-400">還沒有帳號</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {inactiveCount > 0 && (
        <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer w-fit">
          <input id="show-inactive" type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />
          顯示已停用的帳號（{inactiveCount}）
        </label>
      )}

      <RoleGuide roles={roles} />

      {modal?.kind === "create" && (
        <CreateModal roles={roles} onClose={() => setModal(null)}
          onDone={(name, password) => {
            setModal(null);
            setNotice({ text: `已建立「${name}」的帳號。請把登入帳號和下面的初始密碼親自交給對方，並請他登入後到「變更密碼」改成自己的。`, password });
            qc.invalidateQueries({ queryKey: ["users"] });
          }} />
      )}
      {modal?.kind === "edit" && (
        <EditModal user={modal.user} roles={roles} isMe={modal.user.id === me?.id} onClose={() => setModal(null)}
          onDone={() => { setModal(null); setNotice({ text: "帳號已更新" }); qc.invalidateQueries({ queryKey: ["users"] }); }} />
      )}
      {modal?.kind === "reset" && (
        <ResetModal user={modal.user} onClose={() => setModal(null)}
          onDone={(password) => {
            setModal(null);
            setNotice({ text: `已重設「${modal.user.full_name || modal.user.email}」的密碼。請把新密碼親自告訴對方，並請他登入後自行變更。`, password });
          }} />
      )}
    </div>
  );
}

function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-label={label} title={label}
      className="flex items-center gap-1 whitespace-nowrap text-xs px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100">
      {children}<span>{label}</span>
    </button>
  );
}

function NoticeBar({ notice, onClose }: { notice: { text: string; password?: string }; onClose: () => void }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    if (!notice.password) return;
    try { await navigator.clipboard.writeText(notice.password); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* 瀏覽器不允許時，使用者可直接選取文字 */ }
  };
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-900 flex flex-wrap items-start gap-3">
      <div className="flex-1 min-w-[240px] space-y-2">
        <div>{notice.text}</div>
        {notice.password && (
          <div className="flex items-center gap-2">
            <code className="font-mono text-base bg-white border border-blue-200 rounded px-3 py-1 select-all tracking-wider">{notice.password}</code>
            <button onClick={copy} className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border border-blue-300 bg-white hover:bg-blue-100">
              {copied ? <><Check size={13} /> 已複製</> : <><Copy size={13} /> 複製</>}
            </button>
            <span className="text-xs text-blue-700">這組密碼只會顯示這一次</span>
          </div>
        )}
      </div>
      <button onClick={onClose} className="text-xs text-blue-700 hover:underline">關閉</button>
    </div>
  );
}

const ROLE_HINT: Record<string, string> = {
  admin: "全部功能，含帳號管理",
  owner: "看全部資料、簽核報價與採購、匯出報表",
  sales: "客戶、報價、線上詢價、作品案例",
  engineer: "產品/BOM、裁切排版",
  planner: "生產工單、裁切排版、備料",
  warehouse: "庫存、收貨",
  purchaser: "採購單、收貨",
  operator: "現場報工（MES）",
  qc: "品質回報",
};

function RoleGuide({ roles }: { roles: { name: string; display_name: string }[] }) {
  if (roles.length === 0) return null;
  return (
    <details className="bg-white rounded-xl border border-slate-200 p-4 text-sm">
      <summary className="cursor-pointer font-medium text-slate-700">各角色能做什麼</summary>
      <div className="grid sm:grid-cols-2 gap-x-6 gap-y-1.5 mt-3">
        {roles.map((r) => (
          <div key={r.name} className="flex gap-2">
            <span className="font-medium text-slate-700 shrink-0 w-28">{r.display_name}</span>
            <span className="text-slate-500">{ROLE_HINT[r.name] || ""}</span>
          </div>
        ))}
      </div>
    </details>
  );
}

function Shell({ title, children, onClose }: { title: string; children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true" aria-label={title}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-sm">關閉</button>
        </div>
        {children}
      </div>
    </div>
  );
}

const inputCls = "w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

function PasswordField({ id, value, onChange }: { id: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex gap-2">
      <input id={id} value={value} onChange={(e) => onChange(e.target.value)} autoComplete="new-password"
        className={`${inputCls} font-mono tracking-wider`} placeholder="至少 8 個字、含數字" />
      <button type="button" onClick={() => onChange(generatePassword())}
        className="shrink-0 text-xs px-3 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50">隨機產生</button>
    </div>
  );
}

function CreateModal({ roles, onClose, onDone }: {
  roles: { name: string; display_name: string }[]; onClose: () => void; onDone: (name: string, password: string) => void;
}) {
  const [form, setForm] = useState({ full_name: "", email: "", role_name: "sales", password: generatePassword() });
  const [error, setError] = useState("");
  const mut = useMutation({
    mutationFn: () => api.createUser({ ...form, email: form.email.trim(), full_name: form.full_name.trim() }),
    onSuccess: () => onDone(form.full_name.trim(), form.password),
    onError: (e) => setError(errorText(e)),
  });
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.full_name.trim()) return setError("請填姓名");
    if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) return setError("Email 格式不對");
    if (form.password.length < 8 || !/\d/.test(form.password)) return setError("密碼至少 8 個字、要有數字");
    setError("");
    mut.mutate();
  };
  return (
    <Shell title="新增帳號" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label htmlFor="nu-name" className="block text-xs text-slate-500 mb-1">姓名</label>
          <input id="nu-name" value={form.full_name} onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} className={inputCls} placeholder="例如：王小明" />
        </div>
        <div>
          <label htmlFor="nu-email" className="block text-xs text-slate-500 mb-1">登入帳號（Email）</label>
          <input id="nu-email" type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} className={inputCls} placeholder="name@company.com" autoComplete="off" />
        </div>
        <div>
          <label htmlFor="nu-role" className="block text-xs text-slate-500 mb-1">角色</label>
          <select id="nu-role" value={form.role_name} onChange={(e) => setForm((f) => ({ ...f, role_name: e.target.value }))} className={inputCls}>
            {roles.map((r) => <option key={r.name} value={r.name}>{r.display_name}　—　{ROLE_HINT[r.name] || ""}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="nu-pw" className="block text-xs text-slate-500 mb-1">初始密碼</label>
          <PasswordField id="nu-pw" value={form.password} onChange={(v) => setForm((f) => ({ ...f, password: v }))} />
          <p className="text-xs text-slate-400 mt-1">建立後會再顯示一次讓你複製。請對方第一次登入後自己改掉。</p>
        </div>
        {error && <div className="bg-red-50 border border-red-200 text-red-600 rounded-lg p-2.5 text-sm">{error}</div>}
        <div className="flex gap-3 pt-2">
          <button type="button" onClick={onClose} className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg text-sm">取消</button>
          <button type="submit" disabled={mut.isPending} className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:bg-blue-300">
            {mut.isPending ? "建立中…" : "建立帳號"}
          </button>
        </div>
      </form>
    </Shell>
  );
}

function EditModal({ user, roles, isMe, onClose, onDone }: {
  user: AccountUser; roles: { name: string; display_name: string }[]; isMe: boolean; onClose: () => void; onDone: () => void;
}) {
  const [form, setForm] = useState({ full_name: user.full_name || "", role_name: user.role_name || "" });
  const [error, setError] = useState("");
  const mut = useMutation({
    mutationFn: () => api.updateUser(user.id, {
      full_name: form.full_name.trim(),
      ...(isMe || !form.role_name ? {} : { role_name: form.role_name }),
    }),
    onSuccess: onDone,
    onError: (e) => setError(errorText(e)),
  });
  return (
    <Shell title="編輯帳號" onClose={onClose}>
      <form onSubmit={(e) => { e.preventDefault(); if (!form.full_name.trim()) return setError("請填姓名"); mut.mutate(); }} className="space-y-3">
        <div className="text-xs text-slate-500">登入帳號：<span className="font-mono">{user.email}</span>（登入帳號不能修改）</div>
        <div>
          <label htmlFor="eu-name" className="block text-xs text-slate-500 mb-1">姓名</label>
          <input id="eu-name" value={form.full_name} onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} className={inputCls} />
        </div>
        <div>
          <label htmlFor="eu-role" className="block text-xs text-slate-500 mb-1">角色</label>
          <select id="eu-role" value={form.role_name} disabled={isMe}
            onChange={(e) => setForm((f) => ({ ...f, role_name: e.target.value }))} className={`${inputCls} disabled:bg-slate-100`}>
            {!form.role_name && <option value="">未指定角色</option>}
            {roles.map((r) => <option key={r.name} value={r.name}>{r.display_name}</option>)}
          </select>
          {isMe && <p className="text-xs text-slate-400 mt-1">不能改自己的角色，避免把自己鎖在外面。需要的話請另一位管理員處理。</p>}
          {!isMe && <p className="text-xs text-slate-400 mt-1">改了之後立刻生效，對方不用重新登入。</p>}
        </div>
        {error && <div className="bg-red-50 border border-red-200 text-red-600 rounded-lg p-2.5 text-sm">{error}</div>}
        <div className="flex gap-3 pt-2">
          <button type="button" onClick={onClose} className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg text-sm">取消</button>
          <button type="submit" disabled={mut.isPending} className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:bg-blue-300">
            {mut.isPending ? "儲存中…" : "儲存"}
          </button>
        </div>
      </form>
    </Shell>
  );
}

function ResetModal({ user, onClose, onDone }: { user: AccountUser; onClose: () => void; onDone: (password: string) => void }) {
  const [password, setPassword] = useState(generatePassword());
  const [error, setError] = useState("");
  const mut = useMutation({
    mutationFn: () => api.resetUserPassword(user.id, password),
    onSuccess: () => onDone(password),
    onError: (e) => setError(errorText(e)),
  });
  return (
    <Shell title="重設密碼" onClose={onClose}>
      <form onSubmit={(e) => {
        e.preventDefault();
        if (password.length < 8 || !/\d/.test(password)) return setError("密碼至少 8 個字、要有數字");
        mut.mutate();
      }} className="space-y-3">
        <p className="text-sm text-slate-600">幫「{user.full_name || user.email}」設定一組新密碼。舊密碼會立刻失效。</p>
        <div>
          <label htmlFor="rp-pw" className="block text-xs text-slate-500 mb-1">新密碼</label>
          <PasswordField id="rp-pw" value={password} onChange={setPassword} />
        </div>
        <p className="text-xs text-slate-400">對方如果正在使用，已開著的畫面最多 60 分鐘後才會要求重新登入。要立刻踢掉，請用「停用」。</p>
        {error && <div className="bg-red-50 border border-red-200 text-red-600 rounded-lg p-2.5 text-sm">{error}</div>}
        <div className="flex gap-3 pt-2">
          <button type="button" onClick={onClose} className="flex-1 border border-slate-300 text-slate-600 py-2 rounded-lg text-sm">取消</button>
          <button type="submit" disabled={mut.isPending} className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm hover:bg-blue-700 disabled:bg-blue-300">
            {mut.isPending ? "處理中…" : "重設密碼"}
          </button>
        </div>
      </form>
    </Shell>
  );
}
