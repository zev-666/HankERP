"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Plus, Trash2, Play, RotateCw, Scissors, Layers } from "lucide-react";

interface Part { label: string; length_mm: number; width_mm: number; quantity: number; can_rotate: boolean }

// 工廠實際使用的 9 種原板。S 1915×1315 是本廠標準板。
const PRESETS = [
  { name: "S（標準板）", L: 1915, W: 1315 },
  { name: "T", L: 1905, W: 1005 },
  { name: "B", L: 2045, W: 1045 },
  { name: "H", L: 2205, W: 1105 },
  { name: "a", L: 1855, W: 1245 },
  { name: "A2", L: 2365, W: 1415 },
  { name: "L", L: 2565, W: 1315 },
  { name: "M", L: 3095, W: 1585 },
  { name: "2000×1000", L: 2000, W: 1000 },
];

const PART_COLORS = ["#0b6e5f", "#c2703b", "#3d6cb9", "#8a4f9e", "#1f8a5b",
                     "#b5453c", "#2f8c9e", "#8b6a1f", "#6553b5", "#a6455f"];

export default function NestingPage() {
  const qc = useQueryClient();
  const [materialId, setMaterialId] = useState("");
  const [sheetL, setSheetL] = useState(1915);
  const [sheetW, setSheetW] = useState(1315);
  const [kerf, setKerf] = useState(3);
  const [trim, setTrim] = useState(0);
  const [minRem, setMinRem] = useState(50);
  const [remPref, setRemPref] = useState<"any" | "strip" | "long">("any");
  const [parts, setParts] = useState<Part[]>([
    { label: "側板", length_mm: 630, width_mm: 400, quantity: 4, can_rotate: true },
    { label: "層板", length_mm: 630, width_mm: 200, quantity: 6, can_rotate: true },
    { label: "背板", length_mm: 630, width_mm: 300, quantity: 2, can_rotate: true },
  ]);
  const [result, setResult] = useState<any>(null);
  const [compareResult, setCompareResult] = useState<any>(null);
  const [openSheet, setOpenSheet] = useState<number | null>(0);

  const { data: jobs } = useQuery({ queryKey: ["nesting-jobs"], queryFn: () => api.getNestingJobs() });

  const body = () => ({
    material_id: materialId || "00000000-0000-0000-0000-000000000001",
    sheet_length_mm: sheetL, sheet_width_mm: sheetW, kerf_mm: kerf,
    trim_mm: trim, min_remnant_mm: minRem, rem_pref: remPref, parts,
  });

  const calcMut = useMutation({
    mutationFn: () => api.calculateNesting(body()),
    onSuccess: (data) => {
      setResult(data); setCompareResult(null); setOpenSheet(0);
      qc.invalidateQueries({ queryKey: ["nesting-jobs"] });
    },
  });

  const compareMut = useMutation({
    mutationFn: () => api.compareNestingPresets({
      kerf_mm: kerf, trim_mm: trim, min_remnant_mm: minRem, rem_pref: remPref, parts,
    }),
    onSuccess: (data) => { setCompareResult(data); setResult(null); },
  });

  const addPart = () => setParts(p => [...p, { label: `零件${p.length + 1}`, length_mm: 200, width_mm: 150, quantity: 1, can_rotate: true }]);
  const removePart = (i: number) => setParts(p => p.filter((_, idx) => idx !== i));
  const updatePart = (i: number, field: keyof Part, value: any) =>
    setParts(p => p.map((pt, idx) => idx === i ? { ...pt, [field]: value } : pt));

  const need = parts.reduce((s, p) => s + p.quantity, 0);
  const totalArea = parts.reduce((s, p) => s + p.length_mm * p.width_mm * p.quantity, 0);

  // 排法完全相同的板合併顯示（大量訂單可能 59 張板只有 7 種排法）
  const groups: { first: number; nums: number[] }[] = [];
  if (result?.sheets) {
    const idx = new Map<string, number>();
    result.sheets.forEach((sh: any, i: number) => {
      const k = sh.signature;
      if (idx.has(k)) groups[idx.get(k)!].nums.push(i + 1);
      else { idx.set(k, groups.length); groups.push({ first: i, nums: [i + 1] }); }
    });
  }

  const partColor = (label: string) => {
    const i = parts.findIndex(p => p.label === label);
    return PART_COLORS[(i < 0 ? 0 : i) % PART_COLORS.length];
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-semibold text-slate-800">裁切排版最佳化</h1>
        <span className="text-xs text-slate-400">開條裁板（二階段 guillotine）· 含刀序</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* ── 左：設定 ── */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h2 className="text-sm font-medium text-slate-700 mb-4">原板與機台</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">原板型號</label>
                <select
                  value={PRESETS.findIndex(p => p.L === sheetL && p.W === sheetW)}
                  onChange={e => {
                    const i = +e.target.value;
                    if (i >= 0) { setSheetL(PRESETS[i].L); setSheetW(PRESETS[i].W); }
                  }}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value={-1}>自訂尺寸</option>
                  {PRESETS.map((p, i) => (
                    <option key={p.name} value={i}>{p.name}　{p.L} × {p.W} mm</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-500 mb-1">板長 (mm)</label>
                  <input type="number" value={sheetL} onChange={e => setSheetL(+e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1">板寬 (mm)</label>
                  <input type="number" value={sheetW} onChange={e => setSheetW(+e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-500 mb-1">刀縫 (mm)</label>
                  <input type="number" step="0.1" value={kerf} onChange={e => setKerf(+e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs text-slate-500 mb-1">四邊修邊 (mm)</label>
                  <input type="number" step="0.5" value={trim} onChange={e => setTrim(+e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">剩料取向</label>
                <select value={remPref} onChange={e => setRemPref(e.target.value as any)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="any">自動：兩個開條方向都試（建議）</option>
                  <option value="strip">強制沿短邊開條</option>
                  <option value="long">強制沿長邊開條</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">可回收剩料最小邊長 (mm)</label>
                <input type="number" step="5" value={minRem} onChange={e => setMinRem(+e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-500 space-y-0.5">
                <div>原板面積：{(sheetL * sheetW / 1000000).toFixed(2)} m²（{(sheetL * sheetW / 90000).toFixed(1)} 才）</div>
                <div>零件總面積：{(totalArea / 1000000).toFixed(2)} m²（{need} 件）</div>
                <div>理論最少板數：<span className="font-medium text-slate-700">{Math.ceil(totalArea / (sheetL * sheetW))} 張</span></div>
              </div>
            </div>
          </div>

          {/* 零件清單 */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-slate-700">零件清單</h2>
              <button onClick={addPart} className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700">
                <Plus size={13} /> 新增零件
              </button>
            </div>
            <div className="space-y-3">
              {parts.map((p, i) => (
                <div key={i} className="border border-slate-200 rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="w-3 h-3 rounded-sm flex-none" style={{ background: PART_COLORS[i % PART_COLORS.length] }} />
                    <input value={p.label} onChange={e => updatePart(i, "label", e.target.value)}
                      className="flex-1 text-sm font-medium text-slate-700 border-0 focus:outline-none focus:ring-0 p-0" />
                    <button onClick={() => removePart(i)} className="text-slate-300 hover:text-red-500">
                      <Trash2 size={14} />
                    </button>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <input type="number" value={p.length_mm} onChange={e => updatePart(i, "length_mm", +e.target.value)}
                      placeholder="長" className="border border-slate-200 rounded px-2 py-1 text-xs text-center focus:outline-none focus:ring-1 focus:ring-blue-500" />
                    <input type="number" value={p.width_mm} onChange={e => updatePart(i, "width_mm", +e.target.value)}
                      placeholder="寬" className="border border-slate-200 rounded px-2 py-1 text-xs text-center focus:outline-none focus:ring-1 focus:ring-blue-500" />
                    <input type="number" value={p.quantity} onChange={e => updatePart(i, "quantity", +e.target.value)}
                      placeholder="量" className="border border-slate-200 rounded px-2 py-1 text-xs text-center focus:outline-none focus:ring-1 focus:ring-blue-500" />
                  </div>
                  <label className="flex items-center gap-1.5 text-xs text-slate-500">
                    <input type="checkbox" checked={p.can_rotate} onChange={e => updatePart(i, "can_rotate", e.target.checked)} />
                    可旋轉 90°
                  </label>
                </div>
              ))}
            </div>

            <button onClick={() => calcMut.mutate()} disabled={calcMut.isPending || parts.length === 0}
              className="w-full mt-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium py-2.5 rounded-lg text-sm flex items-center justify-center gap-2 transition-colors">
              {calcMut.isPending ? <><RotateCw size={14} className="animate-spin" /> 計算中...</> : <><Play size={14} /> 產生裁切計畫</>}
            </button>
            <button onClick={() => compareMut.mutate()} disabled={compareMut.isPending || parts.length === 0}
              className="w-full mt-2 border border-slate-300 hover:bg-slate-50 text-slate-700 font-medium py-2 rounded-lg text-sm flex items-center justify-center gap-2">
              {compareMut.isPending ? <RotateCw size={14} className="animate-spin" /> : <Layers size={14} />}
              比較 9 種板型，找最省
            </button>
          </div>
        </div>

        {/* ── 右：結果 ── */}
        <div className="lg:col-span-3 space-y-4">
          {compareResult && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <h2 className="text-sm font-medium text-slate-700 mb-3">9 種板型比較</h2>
              {compareResult.best_preset && (
                <div className="mb-3 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
                  ✓ 最省：<strong>{compareResult.best_preset}</strong> — {compareResult.best_sheets_used} 張，
                  利用率 {(compareResult.best_utilization_rate * 100).toFixed(1)}%，
                  共 {compareResult.best_total_cai?.toFixed(1)} 才
                </div>
              )}
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-200">
                      <th className="text-left py-2">板型</th><th className="text-right">尺寸</th>
                      <th className="text-right">張數</th><th className="text-right">利用率</th>
                      <th className="text-right">總才數</th><th className="text-right">刀數</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compareResult.items.map((it: any) => (
                      <tr key={it.name}
                        className={`border-b border-slate-50 cursor-pointer hover:bg-slate-50 ${it.name === compareResult.best_preset ? "font-medium text-blue-700" : "text-slate-600"}`}
                        onClick={() => { setSheetL(it.sheet_length); setSheetW(it.sheet_width); }}>
                        <td className="py-1.5">{it.name}</td>
                        <td className="text-right tabular-nums">{it.sheet_length} × {it.sheet_width}</td>
                        <td className="text-right tabular-nums">{it.impossible ? "—" : it.sheets_used}</td>
                        <td className="text-right tabular-nums">{it.impossible ? "—" : `${(it.utilization_rate * 100).toFixed(1)}%`}</td>
                        <td className="text-right tabular-nums">{it.impossible ? "—" : it.total_cai?.toFixed(1)}</td>
                        <td className="text-right tabular-nums">{it.impossible ? `排不下` : it.total_cuts}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-[11px] text-slate-400">
                「總才數」＝張數 × 單張才數，是實際要買的材料量，比利用率更能反映成本。點任一列可帶入該板型。
              </p>
            </div>
          )}

          {result && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <h2 className="text-sm font-medium text-slate-700 mb-4">排版結果</h2>

              <div className="grid grid-cols-4 gap-3 mb-4">
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-blue-600 tabular-nums">{result.sheets_used}</div>
                  <div className="text-xs text-blue-700 mt-0.5">需要原板（張）</div>
                </div>
                <div className={`rounded-lg p-3 text-center ${result.utilization_rate >= 0.75 ? "bg-green-50" : "bg-amber-50"}`}>
                  <div className={`text-2xl font-bold tabular-nums ${result.utilization_rate >= 0.75 ? "text-green-600" : "text-amber-600"}`}>
                    {result.utilization_rate_pct}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">板材利用率</div>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-slate-700 tabular-nums">
                    {result.placed_count}<span className="text-sm text-slate-400"> / {result.requested_count}</span>
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">已排入 / 需求</div>
                </div>
                <div className="bg-orange-50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-orange-600 tabular-nums">{result.total_cuts}</div>
                  <div className="text-xs text-orange-700 mt-0.5">裁切刀數</div>
                </div>
              </div>

              {result.unplaced?.length > 0 ? (
                <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  ⚠ 有 {result.unplaced.length} 件沒有排進去：
                  {result.unplaced.slice(0, 6).map((u: any) => `${u.label} ${u.length}×${u.width}`).join("、")}
                  {result.unplaced.length > 6 ? " …" : ""}。
                  <span className="text-red-600">（{result.unplaced[0]?.reason}）</span>
                </div>
              ) : (
                <div className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
                  ✓ 全部 {result.requested_count} 件都排得進去，共 {result.sheets_used} 張板，需要下 {result.total_cuts} 刀。
                  第一刀方向為 <strong>{result.axis_label}</strong>。
                </div>
              )}

              {result.band_remnant_count > 0 && (
                <div className="mb-4 rounded-lg border border-teal-200 bg-teal-50 p-3 text-sm text-teal-800">
                  整條剩料：{result.band_remnants.map((b: any) => `${b.length_mm} × ${b.width_mm}`).join("、")}
                  （共 {result.band_remnant_count} 條）。邊是直的，可以直接上架再用。
                </div>
              )}

              {groups.length < result.sheets_used && (
                <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-xs text-slate-600">
                  {result.sheets_used} 張板只有 <strong>{groups.length} 種排法</strong>，相同的已合併，下面每種只列一次。
                </div>
              )}

              {/* 每一種排法：排版圖 ＋ 刀序 */}
              {groups.map((g, gi) => {
                const sh = result.sheets[g.first];
                const n = g.nums.length;
                const label = n === 1 ? `板 ${g.nums[0]}`
                  : (g.nums[n - 1] - g.nums[0] === n - 1 ? `板 ${g.nums[0]}–${g.nums[n - 1]}` : `板 ${g.nums.slice(0, 3).join("、")}…`);
                const pad = 28;
                const vb = `${-pad} ${-pad} ${sheetL + pad * 2} ${sheetW + pad * 2}`;
                const fs = Math.max(sheetL, sheetW) / 55;
                const open = openSheet === gi;
                return (
                  <div key={gi} className="border border-slate-200 rounded-lg mb-3 overflow-hidden">
                    <button onClick={() => setOpenSheet(open ? null : gi)}
                      className="w-full flex items-center gap-2 px-3 py-2 bg-slate-50 hover:bg-slate-100 text-left">
                      <span className="font-mono text-xs font-bold text-white bg-slate-700 rounded px-2 py-0.5">{label}</span>
                      {n > 1 && <span className="text-xs font-medium text-blue-600 bg-blue-50 rounded-full px-2 py-0.5">× {n} 張</span>}
                      <span className="text-xs text-slate-500 font-mono">
                        {sh.strips_count} 條 · {sh.items_count} 件{n > 1 ? "/張" : ""} · 利用率 {(sh.utilization_rate * 100).toFixed(1)}% · {sh.cuts_count} 刀{n > 1 ? "/張" : ""}
                      </span>
                      <span className="ml-auto text-xs text-slate-400">{open ? "收合" : "展開"}</span>
                    </button>

                    {open && (
                      <div className="p-3 space-y-3">
                        <svg viewBox={vb} className="w-full h-auto border border-slate-100 rounded bg-slate-50">
                          <rect x={0} y={0} width={sheetL} height={sheetW} fill="#fff" stroke="#cbd5e1" strokeWidth={Math.max(1.5, sheetL / 700)} />
                          {trim > 0 && (
                            <rect x={trim} y={trim} width={sheetL - 2 * trim} height={sheetW - 2 * trim}
                              fill="none" stroke="#94a3b8" strokeWidth={sheetL / 1400} strokeDasharray={`${sheetL / 110} ${sheetL / 150}`} />
                          )}
                          {sh.remnants.filter((r: any) => r.band).map((r: any, i: number) => (
                            <rect key={`b${i}`} x={r.x} y={r.y} width={r.w_mm} height={r.h_mm}
                              fill="#0d9488" fillOpacity={0.08} stroke="#0d9488" strokeWidth={sheetL / 1400}
                              strokeDasharray={`${sheetL / 90} ${sheetL / 140}`} />
                          ))}
                          {sh.strips.map((st: any, si: number) =>
                            st.items.map((it: any, ii: number) => (
                              <g key={`${si}-${ii}`}>
                                <rect x={it.x} y={it.y} width={it.length} height={it.width}
                                  fill={partColor(it.part_label)} fillOpacity={0.18}
                                  stroke={partColor(it.part_label)} strokeWidth={Math.max(1.4, sheetL / 750)} />
                                {Math.min(it.length, it.width) > fs * 2.4 && (
                                  <text x={it.x + it.length / 2} y={it.y + it.width / 2} fontSize={fs}
                                    fill={partColor(it.part_label)} textAnchor="middle" dominantBaseline="central">
                                    {it.length}×{it.width}
                                  </text>
                                )}
                              </g>
                            ))
                          )}
                          {sh.cuts.map((c: any) => {
                            const isH = c.direction === "橫切";
                            const isRip = c.phase === "開條";
                            // v2.3.4：修窄刀（比條寬窄的零件再修一刀）用琥珀色點線，跟 cutplan 一致
                            const isNarrow = c.phase === "修窄";
                            return (
                              <line key={c.seq}
                                x1={isH ? c.from_mm : c.position_mm} y1={isH ? c.position_mm : c.from_mm}
                                x2={isH ? c.to_mm : c.position_mm} y2={isH ? c.position_mm : c.to_mm}
                                stroke={isNarrow ? "#b45309" : "#dc2626"} strokeWidth={isRip ? sheetL / 700 : sheetL / 1100}
                                strokeDasharray={isRip ? "" : isNarrow ? `${sheetL / 400} ${sheetL / 250}` : `${sheetL / 100} ${sheetL / 200}`}
                                opacity={isRip ? 1 : 0.75} />
                            );
                          })}
                          <text x={sheetL / 2} y={-8} fontSize={fs * 0.95} fill="#94a3b8" textAnchor="middle">{sheetL} mm</text>
                          <text x={-8} y={sheetW / 2} fontSize={fs * 0.95} fill="#94a3b8" textAnchor="middle"
                            transform={`rotate(-90 ${-8} ${sheetW / 2})`}>{sheetW} mm</text>
                        </svg>

                        <div className="flex items-center gap-4 text-[11px] text-slate-500">
                          <span className="flex items-center gap-1.5"><span className="inline-block w-5 h-0.5 bg-red-600" />開條刀（整刀切穿）</span>
                          <span className="flex items-center gap-1.5"><span className="inline-block w-5 border-t border-dashed border-red-600" />條內分件刀</span>
                          <span className="flex items-center gap-1.5"><span className="inline-block w-5 border-t-2 border-dotted border-amber-700" />窄件修一刀</span>
                          <span className="flex items-center gap-1.5"><span className="inline-block w-3 h-3 border border-dashed border-teal-600 bg-teal-50" />整條剩料</span>
                        </div>

                        <div>
                          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-600 mb-1.5">
                            <Scissors size={12} /> 裁切順序（{sh.cuts.length} 刀{n > 1 ? "／張" : ""}）
                          </div>
                          <div className="max-h-64 overflow-y-auto border border-slate-100 rounded">
                            <table className="w-full text-[11px]">
                              <thead className="sticky top-0 bg-slate-50">
                                <tr className="text-slate-400">
                                  <th className="text-right py-1.5 px-2">#</th><th className="text-left">階段</th>
                                  <th className="text-left">方向</th><th className="text-right">基準位置</th>
                                  <th className="text-right px-2">刀長</th><th className="text-left">說明</th>
                                </tr>
                              </thead>
                              <tbody>
                                {sh.cuts.map((c: any) => (
                                  <tr key={c.seq} className="border-t border-slate-50 text-slate-600">
                                    <td className="text-right py-1 px-2 tabular-nums">{String(c.seq).padStart(2, "0")}</td>
                                    <td>
                                      <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                                        c.phase === "開條" ? "bg-orange-50 text-orange-700"
                                        : c.phase === "分件" ? "bg-teal-50 text-teal-700"
                                        : c.phase === "修窄" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-500"}`}>
                                        {c.phase}
                                      </span>
                                    </td>
                                    <td>{c.direction}</td>
                                    <td className="text-right tabular-nums">{c.position_mm}</td>
                                    <td className="text-right px-2 tabular-nums">{c.length_mm}</td>
                                    <td className="text-slate-400">{c.note}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>

                        {sh.remnants.filter((r: any) => r.usable).length > 0 && (
                          <div>
                            <div className="text-xs font-medium text-slate-600 mb-1.5">
                              可回收剩料（{sh.remnants.filter((r: any) => r.usable).length}{n > 1 ? "／張" : ""}）
                            </div>
                            <div className="space-y-1">
                              {sh.remnants.filter((r: any) => r.usable).map((r: any, i: number) => (
                                <div key={i} className="flex items-center gap-2 text-[11px] bg-amber-50 rounded px-2.5 py-1.5">
                                  <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                                    r.grade === "A" ? "bg-green-100 text-green-700"
                                    : r.grade === "B" ? "bg-amber-100 text-amber-700" : "bg-slate-200 text-slate-600"}`}>{r.grade}</span>
                                  <span className="font-medium text-slate-700 tabular-nums">{r.length_mm} × {r.width_mm} mm</span>
                                  <span className="text-slate-400">{r.band ? "整條" : "零星"}</span>
                                  <span className="ml-auto text-amber-700 tabular-nums">{r.area_cai.toFixed(2)} 才</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              <p className="text-[11px] text-slate-400 mt-2">
                等級：A ≥ 300×300 mm（一才以上）· B ≥ 150×150 mm · C 其餘。
                引擎 <span className="font-mono">{result.engine}</span> · 策略 <span className="font-mono">{result.strategy}</span>
                （已自動比較開條方向、排序、擺向與填法的所有組合）
              </p>
            </div>
          )}

          {/* 歷史 */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h2 className="text-sm font-medium text-slate-700 mb-3">排版歷史</h2>
            <div className="space-y-2">
              {(jobs?.data || []).slice(0, 8).map((job: any) => (
                <div key={job.id} className="flex items-center justify-between text-sm border-b border-slate-50 pb-2">
                  <span className="font-mono text-xs text-slate-500">{job.id.slice(-8)}</span>
                  <span className="text-slate-700">{job.sheets_used} 張</span>
                  <span className={`font-medium ${(job.utilization_rate * 100) >= 85 ? "text-green-600" : "text-amber-500"}`}>
                    {((job.utilization_rate || 0) * 100).toFixed(1)}%
                  </span>
                  <span className="text-xs text-slate-400">{new Date(job.created_at).toLocaleDateString("zh-TW")}</span>
                </div>
              ))}
              {(!jobs?.data || jobs.data.length === 0) && (
                <div className="text-slate-400 text-sm text-center py-4">尚無排版記錄</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
