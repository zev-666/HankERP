"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Plus, Trash2, Play, RotateCw } from "lucide-react";

interface Part { label: string; length_mm: number; width_mm: number; quantity: number; can_rotate: boolean }

export default function NestingPage() {
  const qc = useQueryClient();
  const [materialId, setMaterialId] = useState("");
  const [sheetL, setSheetL] = useState(2000);
  const [sheetW, setSheetW] = useState(1000);
  const [kerf, setKerf] = useState(3);
  const [parts, setParts] = useState<Part[]>([
    { label: "正面板", length_mm: 500, width_mm: 400, quantity: 2, can_rotate: true },
    { label: "側板", length_mm: 300, width_mm: 400, quantity: 2, can_rotate: true },
  ]);
  const [result, setResult] = useState<any>(null);

  const { data: jobs } = useQuery({ queryKey: ["nesting-jobs"], queryFn: () => api.getNestingJobs() });

  const calcMut = useMutation({
    mutationFn: () => api.calculateNesting({
      material_id: materialId || "00000000-0000-0000-0000-000000000001",
      sheet_length_mm: sheetL,
      sheet_width_mm: sheetW,
      kerf_mm: kerf,
      parts,
    }),
    onSuccess: (data) => {
      setResult(data);
      qc.invalidateQueries({ queryKey: ["nesting-jobs"] });
    },
  });

  const addPart = () => setParts(p => [...p, { label: `零件${p.length + 1}`, length_mm: 200, width_mm: 150, quantity: 1, can_rotate: true }]);
  const removePart = (i: number) => setParts(p => p.filter((_, idx) => idx !== i));
  const updatePart = (i: number, field: keyof Part, value: any) =>
    setParts(p => p.map((pt, idx) => idx === i ? { ...pt, [field]: value } : pt));

  const totalArea = parts.reduce((s, p) => s + p.length_mm * p.width_mm * p.quantity, 0);
  const sheetArea = sheetL * sheetW;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold text-slate-800">裁切排版最佳化</h1>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: Config */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h2 className="text-sm font-medium text-slate-700 mb-4">板材設定</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1">原板長度 (mm)</label>
                <input type="number" value={sheetL} onChange={e => setSheetL(+e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">原板寬度 (mm)</label>
                <input type="number" value={sheetW} onChange={e => setSheetW(+e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">刀縫寬度 (mm)</label>
                <input type="number" value={kerf} onChange={e => setKerf(+e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-500">
                <div>原板面積：{(sheetL * sheetW / 1000000).toFixed(2)} m²</div>
                <div>零件總面積：{(totalArea / 1000000).toFixed(2)} m²</div>
                <div>理論最少板數：<span className="font-medium text-slate-700">{Math.ceil(totalArea / sheetArea)} 張</span></div>
              </div>
            </div>
          </div>

          {/* Parts list */}
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
                  <div className="flex items-center justify-between">
                    <input value={p.label} onChange={e => updatePart(i, "label", e.target.value)}
                      className="text-sm font-medium text-slate-700 border-none outline-none bg-transparent w-32" />
                    <button onClick={() => removePart(i)} className="text-slate-400 hover:text-red-500">
                      <Trash2 size={13} />
                    </button>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div>
                      <div className="text-[10px] text-slate-400">長 (mm)</div>
                      <input type="number" value={p.length_mm} onChange={e => updatePart(i, "length_mm", +e.target.value)}
                        className="w-full border border-slate-200 rounded px-2 py-1 text-xs" />
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-400">寬 (mm)</div>
                      <input type="number" value={p.width_mm} onChange={e => updatePart(i, "width_mm", +e.target.value)}
                        className="w-full border border-slate-200 rounded px-2 py-1 text-xs" />
                    </div>
                    <div>
                      <div className="text-[10px] text-slate-400">數量</div>
                      <input type="number" value={p.quantity} onChange={e => updatePart(i, "quantity", +e.target.value)}
                        className="w-full border border-slate-200 rounded px-2 py-1 text-xs" min={1} />
                    </div>
                  </div>
                  <label className="flex items-center gap-1.5 text-xs text-slate-500 cursor-pointer">
                    <input type="checkbox" checked={p.can_rotate} onChange={e => updatePart(i, "can_rotate", e.target.checked)} />
                    可旋轉（無紋路限制）
                  </label>
                </div>
              ))}
            </div>
            <button
              onClick={() => calcMut.mutate()}
              disabled={calcMut.isPending || parts.length === 0}
              className="w-full mt-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium py-2.5 rounded-lg text-sm flex items-center justify-center gap-2 transition-colors"
            >
              {calcMut.isPending ? <><RotateCw size={14} className="animate-spin" /> 計算中...</> : <><Play size={14} /> 執行裁切最佳化</>}
            </button>
          </div>
        </div>

        {/* Right: Result */}
        <div className="lg:col-span-3 space-y-4">
          {result && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <h2 className="text-sm font-medium text-slate-700 mb-4">排版結果</h2>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="bg-green-50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-green-600">{result.utilization_rate}</div>
                  <div className="text-xs text-green-700 mt-0.5">板材利用率</div>
                </div>
                <div className="bg-blue-50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-blue-600">{result.sheets_used}</div>
                  <div className="text-xs text-blue-700 mt-0.5">需要張數</div>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-slate-600">{result.remnants?.length || 0}</div>
                  <div className="text-xs text-slate-500 mt-0.5">可回收剩料</div>
                </div>
              </div>

              {/* Visual nesting canvas per sheet */}
              {Array.from({ length: result.sheets_used }).map((_, si) => {
                const sheetPlacements = result.placements?.filter((p: any) => p.sheet_index === si) || [];
                const scale = Math.min(500 / sheetL, 220 / sheetW);
                return (
                  <div key={si} className="border border-slate-200 rounded-lg p-3 mb-3">
                    <div className="text-xs font-medium text-slate-600 mb-2">第 {si + 1} 張板</div>
                    <div className="relative bg-slate-100 rounded border border-slate-300 overflow-hidden"
                      style={{ width: sheetL * scale, height: sheetW * scale, maxWidth: "100%" }}>
                      {sheetPlacements.map((pl: any, pi: number) => {
                        const part = parts.find(p => p.label === pl.part_id) || parts[0];
                        const w = pl.rotated ? part?.width_mm : part?.length_mm;
                        const h = pl.rotated ? part?.length_mm : part?.width_mm;
                        const colors = ["#93c5fd","#86efac","#fcd34d","#f9a8d4","#a5b4fc","#6ee7b7"];
                        return (
                          <div key={pi} className="absolute border border-white flex items-center justify-center text-[8px] font-medium text-white"
                            style={{
                              left: pl.x * scale, top: pl.y * scale,
                              width: (w || 200) * scale, height: (h || 150) * scale,
                              background: colors[pi % colors.length], opacity: 0.85,
                            }}>
                            {pl.part_id}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}

              {/* Remnants */}
              {result.remnants?.length > 0 && (
                <div>
                  <div className="text-xs font-medium text-slate-600 mb-2">可回收剩料</div>
                  <div className="space-y-1">
                    {result.remnants.map((r: any, i: number) => (
                      <div key={i} className="flex items-center justify-between text-xs bg-amber-50 rounded px-3 py-1.5">
                        <span className="text-slate-600">第{r.sheet_index + 1}張板 — {r.length_mm.toFixed(0)} × {r.width_mm.toFixed(0)} mm</span>
                        <span className="text-amber-700 font-medium">{(r.area_mm2 / 90000).toFixed(1)} 才</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* History */}
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
